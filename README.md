recover-site-from-cache
=======================

Small script to recover wordpress site from google cache. In case you've dropped your database and have no backups

It's not intended to be used as is, rather modified to your personal needs, especially databases and parsing html of pages.

requirements
============
Requires basic knowledge of python and jquery-like grabbing of elements (using pyquery). Also you have to know what you're doing.

Script uses mongodb to store local copies of fetched urls and connects to wordpress database locally.
You can modify those setting in db.py file.

Requirements are described in requirements.txt


usage
===========

Script has two modes of operating:

 1. Parsing urls from wp's sitemap.xml
 2. Fetching specified url from webcache and recursively crawling rest of urls from it (unreliable and buggy)

__to run it__

```
python main.py 
```
By default it will look for sitemap.xml in current dir.

Arguments:

```
  -s SITEMAPFILE, --sitemap SITEMAPFILE
                        provide path to a sitemap file and grab urls from it
  -c CRAWL_URL, --crawl CRAWL_URL
                        Url to start recursive crawling (without sitemap)
  -t TIMER, --timeout TIMER
                        Timeout between requests to google cache, to avoid
                        being banned, default = 61
```
