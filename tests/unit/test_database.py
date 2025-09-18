# tests/unit/test_database.py
import types
import pytest

import app.database as database  # замените на ваш путь


class DummyDB:
    pass


class DummyClient:
    def __init__(self, uri):
        # сохраняем, что было передано
        self._uri = uri
        # эмулируем доступ к атрибуту .apartments
        self.apartments = DummyDB()


def test_get_db_returns_apartments(monkeypatch):
    captured = {}

    def fake_client(uri):
        captured["uri"] = uri
        return DummyClient(uri)

    # Подменяем MongoClient в тестируемом модуле
    monkeypatch.setattr(database, "MongoClient", fake_client)

    db = database.get_db()

    # Проверяем, что вызвали с правильным URI
    assert captured["uri"] == "mongodb://mongo:27017/mydatabase"

    # Проверяем, что вернулся именно DummyDB (экземпляр apartments)
    assert isinstance(db, DummyDB)


def test_get_db_multiple_calls_create_new_clients(monkeypatch):
    calls = []

    def fake_client(uri):
        calls.append(uri)
        return DummyClient(uri)

    monkeypatch.setattr(database, "MongoClient", fake_client)

    db1 = database.get_db()
    db2 = database.get_db()

    # Должны быть разные объекты DummyDB
    assert db1 is not db2
    # Но оба должны быть DummyDB
    assert isinstance(db1, DummyDB)
    assert isinstance(db2, DummyDB)
    # И MongoClient вызывался дважды
    assert calls == [
        "mongodb://mongo:27017/mydatabase",
        "mongodb://mongo:27017/mydatabase",
    ]
