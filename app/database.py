from pymongo import MongoClient


def get_apartments_db():
    client = MongoClient("mongodb://mongo:27017/mydatabase")
    db = client.apartments
    return db


def get_rental_db():
    client = MongoClient("mongodb://mongo:27017/mydatabase")
    db = client.rental
    return db
