from pymongo import MongoClient, errors
from contextlib import contextmanager


@contextmanager
def get_apartments_db():
    client = None
    try:
        client = MongoClient("mongodb://mongo:27017/mydatabase")
        db = client.apartments
        yield db
    except errors.ConnectionFailure as e:
        raise RuntimeError(f"Не удалось подключиться к MongoDB: {e}")
    finally:
        if client:
            client.close()


@contextmanager
def get_rental_db():
    client = None
    try:
        client = MongoClient("mongodb://mongo:27017/mydatabase")
        db = client.rental
        yield db
    except errors.ConnectionFailure as e:
        raise RuntimeError(f"Не удалось подключиться к MongoDB: {e}")
    finally:
        if client:
            client.close()


def get_client():
    client = MongoClient("mongodb://mongo:27017/mydatabase")
    return client