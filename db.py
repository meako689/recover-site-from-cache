from sqlalchemy import create_engine, MetaData

from pymongo import MongoClient
client = MongoClient()
db = client.wpsave
Posts = db.posts


wpdb = create_engine('mysql+mysqldb://root:@127.0.0.1:3306/wp-db')
m = MetaData()
m.reflect(wpdb)


WpTermTaxonomy = m.tables['wp_term_taxonomy']
WpPosts = m.tables['wp_posts']
WpTerms = m.tables['wp_terms']
WpTermRelationships = m.tables['wp_term_relationships']
