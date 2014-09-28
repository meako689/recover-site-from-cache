import requests
import xmltodict
from pyquery import PyQuery
from db import posts 

sitemapfile = 'sitemap.xml'
cacheurl = "http://webcache.googleusercontent.com/search?q=cache:"

def main():
    parsedurls = 0
    failedurls = 0
    file = open(sitemapfile)
    data = xmltodict.parse(file)
    items = data['urlset']['url']
    print "Found {} entries in sitemap".format(len(items))
    for item in items:
        url = item['loc']
        print "checking {}".format(url)
        saved = posts.find_one({'url':url})
        if not saved:
            print "Url was not grabbed. Grabbing..."
            response = requests.get(cacheurl+url)
            if response.status_code == 200:
                raw_content = response.content
                posts.insert({'url':url, 'raw_content':raw_content})
                print "Url saved."
                parsedurls += 1
            else:
                print "Could'nt get url"
                failedurls += 1
                import ipdb; ipdb.set_trace()

    print "Done, successfully saved {} urls, failed {} urls".format(parsedurls, failedurls)

main()


    
