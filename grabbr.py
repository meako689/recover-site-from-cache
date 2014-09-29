import datetime
import urllib
import time
import requests
import xmltodict
from pyquery import PyQuery
from db import Posts,WpPosts, WpTerms, WpTermTaxonomy, WpTermRelationships, wpdb
from sqlalchemy import and_, or_






class WpGrabbr(object):
    def __init__(self):
        self.sitemapfile = 'sitemap.xml'
        self.cacheurl = "http://webcache.googleusercontent.com/search?q=cache:"
        self.loadedurls = 0
        self.parsedurls = 0
        self.insertedurls = 0
        self.failedurls = 0
        self.s = requests.Session()
        self.s.headers['User-Agent']= 'Mozilla/5.0 (X11; Linux x86_64; rv:31.0) Gecko/20100101 Firefox/31.0'
        self.s.headers['Accept']= 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        self.timer = 61
        
    def grab_url(self, url):
        """docstring for parse_url"""
        try:
            response = self.s.get(cacheurl+url)
            if response.status_code == 200:
                raw_content = response.content
                Posts.insert({'url':url, 'raw_content':raw_content})
                print "Url saved."
                self.loadedurls += 1
                time.sleep(self.timer)
            elif response.status_code == 503:
                import ipdb; ipdb.set_trace()
            else:
                print "Could'nt get url"
                print response.url
                self.failedurls += 1
        except Exception as e:
            print "Failed with e:", e
        return Posts.find_one({'url':url})

    def parse_grabbed(self, url, item):
        raw_data = item['raw_content']
        parsd = PyQuery(raw_data)
        content = parsd('div.entry-content').html()
        title = parsd('h1.entry-title').html()
        tags = []
        for raw_tag in parsd('ul.tag-list>li>a'):
            tag = {'title':raw_tag.text,
                   'slug':urllib.pathname2url(
                       raw_tag.attrib['href'].split('/')[-1].encode('utf8')
                    )
                }
            tags.append(tag)
        raw_postsed_date = parsd('header .entry-meta time.entry-date')[0].attrib['datetime']
        posted_date = datetime.datetime.strptime(raw_postsed_date[:-6],"%Y-%m-%dT%H:%M:%S")
        raw_category = parsd('header a')[-2]
        category = {'title':raw_category.text,
                    'slug':urllib.pathname2url(
                        raw_category.attrib['href'].split('/')[-1].encode('utf8')
                    )}
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
        return Posts.find_one({'url':url})

    def insert_into_wp(self, item):
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
                    'name':tag.get('title')})
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

        insert_taxonomy_relation(item['category'], 'category')



        Posts.update({'url':item['url']},{'$set':{
            'inserted':True}})
        self.insertedurls += 1

    def loadsitemap(self, sitemapfile):
        file = open(sitemapfile)
        data = xmltodict.parse(file)
        items = data['urlset']['url']
        return items

    def main(self):
        print "Found {} entries in sitemap".format(len(items))
        items = self.loadsitemap(self.sitemapfile)
        for item in items:
            url = item['loc']
            print "checking {}".format(url)
            item = Posts.find_one({'url':url})
            if not item:
                print "Url was not grabbed. Grabbing..."
                item = self.grab_url(url)
                if not item:
                    continue

            if not item.get('parsed'):
                print "Parsing url..."
                item = self.parse_grabbed(url, item)
                print "Parsing done"
            wp_post = wpdb.execute(WpPosts.select(
                        WpPosts.c.post_name == item['url'])).fetchone()
            #elif not item.get('inserted') and not wp_post:
            elif not wp_post:
                print "Inserting into wp db..."
                self.insert_into_wp(item)
                print "Done inserting."
            else:
                print "Already processed"

            print "Done"
            print "successfully grabbed {loadedurls}".format(self.loadedurls)
            print "successfully parsed {parsed}".format(self.parsedurls)
            print "successfully inserted {inserted}".format(self.insertedurls)
            print "failed {failed} urls".format(self.failedurls)
