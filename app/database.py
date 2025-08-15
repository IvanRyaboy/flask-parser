from pymongo import MongoClient


def get_db():
    client = MongoClient("mongodb://mongo:27017/mydatabase")
    db = client.apartments
    return db
