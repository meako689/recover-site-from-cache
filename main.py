from argparse import ArgumentParser
from grabbr import WpGrabbr

parser = ArgumentParser()
parser.add_argument("-s", "--sitemap", dest="sitemapfile", default='sitemap.xml',
                  help="Grab from sitemap, provide path to a file")
parser.add_argument("-c", "--crawl",
                  dest="crawl_url",
                  help="Url to start crawling")
parser.add_argument("-t", "--timeout", dest="timer", default=61,
                  help="Timeout between requests to google cache, to avoid being banned, default = 61s")


arguments = parser.parse_args()

wg = WpGrabbr(arguments.sitemapfile, arguments.timer)
if arguments.sitemapfile:
    wg.parse_from_sitemap()
if arguments.crawl_url:
    wg.crawl_missing_urls(arguments.crawl_url)
