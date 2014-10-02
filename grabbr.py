import datetime
import urllib
import time
import requests
import xmltodict
from pyquery import PyQuery
from db import Posts,WpPosts, WpTerms, WpTermTaxonomy, WpTermRelationships, wpdb
from sqlalchemy import and_, or_






class WpGrabbr(object):
    def __init__(self, sitemapfile='sitemap.xml', timer=61):
        self.sitemapfile = sitemapfile
        self.timer = timer
        self.cacheurl = "http://webcache.googleusercontent.com/search?q=cache:"
        self.loadedurls = 0
        self.parsedurls = 0
        self.insertedurls = 0
        self.failedurls = 0
        self.s = requests.Session()
        self.s.headers['User-Agent']= 'Mozilla/5.0 (X11; Linux x86_64; rv:31.0) Gecko/20100101 Firefox/31.0'
        self.s.headers['Accept']= 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'

        self.grabbed_additional_urls = set([])

    def crawl_missing_urls(self, url, grabbed=None):
        print "Crawling internal urls from {}".format(url)
        if not grabbed: grabbed = self.check_url(url)
        self.grabbed_additional_urls.add(url)
        if not grabbed: return

        parsd = PyQuery(grabbed['raw_content'])
        all_urls = parsd('a')
        parenturl = url.split('/')[2]
        internal_urls = set(filter(lambda a: a and\
                parenturl in a and\
                'category' not in a and\
                'author' not in a and\
                'feed' not in a and\
                'tag' not in a and\
                '#' not in a and\
                '&' not in a and\
                '.' not in a.split('/')[-1] and\
                'http://'+parenturl+'/' != a and\
                a not in self.grabbed_additional_urls,
                [a.attrib.get('href') for a in all_urls]))

        grabbedurls = [self.check_url(iurl) for iurl in internal_urls]
        for gurl in grabbedurls:
            if gurl and gurl.get('url'): self.crawl_missing_urls(gurl['url'], gurl) 


        
    def grab_url(self, url):
        """Grab url into database"""
        response = self.s.get(self.cacheurl+url)
        if response.status_code == 200:
            raw_content = response.content
            Posts.insert({'url':url, 'raw_content':raw_content})
            print "Url saved."
            self.loadedurls += 1
            print "Sleeping for {} seconds".format(self.timer)
            time.sleep(self.timer)
        elif response.status_code == 503:
            import ipdb; ipdb.set_trace()
        else:
            print "Could'nt get url"
            print response.url
            self.failedurls += 1
        return Posts.find_one({'url':url})

    def parse_grabbed(self, url, item, datestr=u'2014-07-18T11:20:24+00:00'):
        """Parse grabbed item, extract title content, tags"""
        raw_data = item['raw_content']
        parsd = PyQuery(raw_data)
        content_el = parsd('div.entry-content')
        if not content_el:
            content_el = parsd('.post-content')
        content = content_el.html()
        title = parsd('h1').html()
        tags = []
        for raw_tag in parsd('ul.tag-list>li>a'):
            tag = {'title':raw_tag.text,
                   'slug':urllib.pathname2url(
                       raw_tag.attrib['href'].split('/')[-1].encode('utf8')
                    )
                }
            tags.append(tag)
        raw_posted_date = parsd('header .entry-meta time.entry-date')
        if raw_posted_date:
            raw_posted_date_text = raw_posted_date[0].attrib['datetime']
        else:
            print "Failed to parse date!"
            raw_posted_date_text=datestr
        print "Setting post date: {}".format(raw_posted_date_text)
        posted_date = datetime.datetime.strptime(raw_posted_date_text[:-6],"%Y-%m-%dT%H:%M:%S")
        raw_category = None
        for potential_category in parsd('a'):
            if potential_category.attrib.get('rel'):
                if 'tag' in potential_category.attrib.get('rel'):
                    raw_category = potential_category
                    break
        if raw_category:
            category = {'title':raw_category.text,
                        'slug':urllib.pathname2url(
                            raw_category.attrib['href'].split('/')[-1].encode('utf8')
                        )}
        else:
            category = None
        author_raw = parsd('header vcard>a')
        author = author_raw[0].text if author_raw else None

        Posts.update({'url':url},{'$set':{
            'slug':url.split('/')[-1],
            'content':content,
            'title':title,
            'tags':tags,
            'posted_date':posted_date,
            'category':category,
            'author':author,
            'parsed':True
        }})
        self.parsedurls += 1
        time.sleep(1)
        return Posts.find_one({'url':url})

    def insert_into_wp(self, item):
        """Insert into wp database"""
        i = WpPosts.insert({
            'post_author':1, #TODO
            'post_date':item.get('posted_date'),
            'post_date_gmt':item.get('posted_date'),
            'post_modified':item.get('posted_date'),
            'post_modified_gmt':item.get('posted_date'),
            'post_content':item.get('content'),
            'post_title':item.get('title'),
            'post_name':item.get('slug'),
            'post_status':'publish',
            'comment_status':'open',
            'ping_status':'open'
        })

        res = wpdb.execute(i)
        post_id = res.inserted_primary_key[0]

        def insert_taxonomy_relation(tag, taxonomy_type):
            """Helper to mange wp's tags and categories"""
            wptag = wpdb.execute(
                    WpTerms.select(
                        WpTerms.c.slug==tag['slug'])
                    ).fetchone()
            if wptag:
                wptag_id = wptag[0]
                taxonomy = wpdb.execute(WpTermTaxonomy.select(and_(
                    WpTermTaxonomy.c.term_id == wptag_id,
                    WpTermTaxonomy.c.taxonomy == taxonomy_type))).fetchone()
                taxonomy_id = taxonomy[0] if taxonomy else None
            else:
                i = WpTerms.insert({'slug':tag.get('slug'),
                    'name':tag.get('title','None')})
                res = wpdb.execute(i)
                wptag_id = res.inserted_primary_key[0]

                i = WpTermTaxonomy.insert({'term_id':wptag_id,
                    'taxonomy': taxonomy_type})
                res = wpdb.execute(i)
                taxonomy_id = res.inserted_primary_key[0]

            if wptag_id != None and taxonomy_id != None:
                i = WpTermRelationships.insert({'object_id':post_id,
                    'term_taxonomy_id':taxonomy_id})
                wpdb.execute(i)


        for tag in item['tags']:
            insert_taxonomy_relation(tag, 'post_tag')

        if item.get('category'):
            insert_taxonomy_relation(item['category'], 'category')



        Posts.update({'url':item['url']},{'$set':{
            'inserted':True}})
        self.insertedurls += 1

    def load_sitemap(self, sitemapfile):
        """Parse sitemap"""
        file = open(sitemapfile)
        data = xmltodict.parse(file)
        items = data['urlset']['url']
        print "Found {} entries in sitemap".format(len(items))
        return items

    def check_url(self, url, datestr=None):
        """Check url and if not loaded - grab, parse, and upload to wp.
        if load, just return parsed item
        """
        print "checking {}".format(url)
        item = Posts.find_one({'url':url})
        if not item:
            print "Url was not grabbed. Grabbing..."
            try:
                item = self.grab_url(url)
                if not item:
                    return
            except Exception as e:
                print "Failed grabbing with e:", e
                self.failedurls += 1
                return

        if not item.get('parsed') or not item.get('content'):
            print "Parsing item..."
            try:
                item = self.parse_grabbed(url, item, datestr=datestr)
            except Exception as e:
                print "Failed parsing with e:", e
                self.failedurls += 1
                return
            print "Parsing done."

        wp_post = wpdb.execute(WpPosts.select(
                    WpPosts.c.post_name == item['slug'])).fetchone()
        if not wp_post:
            print "Inserting into wp db..."
            try:
                self.insert_into_wp(item)
            except Exception as e:
                print "Failed inserting with e:", e
                self.failedurls += 1
                return
            print "Done inserting."
        else:
            print "Already processed"

        return item


    def parse_from_sitemap(self):
        """Grab and load all urls from sitemap"""
        items = self.load_sitemap(self.sitemapfile)
        for item in items:
            url = item['loc']
            datestr = item['lastmod']
            self.check_url(url, datestr)

        self.print_finished()

    def print_finished(self):
        print "Done"
        print "successfully grabbed {}".format(self.loadedurls)
        print "successfully parsed {}".format(self.parsedurls)
        print "successfully inserted {}".format(self.insertedurls)
        print "failed {} urls".format(self.failedurls)
