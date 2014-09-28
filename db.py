from pymongo import MongoClient
client = MongoClient() 
db = client.wpsave
posts = db.posts


