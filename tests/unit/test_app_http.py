# tests/unit/test_main_http.py
import importlib
import sys
import types

import pytest


# --- простые фейки БД/коллекции ---

class FakeCollection:
    def __init__(self, docs=None):
        self._docs = list(docs or [])

    def find_one(self, filter=None):
        if not filter:
            return self._docs[0] if self._docs else None
        if "_id" in filter:
            for d in self._docs:
                if d.get("_id") == filter["_id"]:
                    return d
        return None


class FakeDB:
    def __init__(self, docs=None):
        self.apartments = FakeCollection(docs)


# --- фикстура импорта модуля с подменами ---

@pytest.fixture
def import_main_module(monkeypatch):
    def _import(docs=None):
        # database.get_apartments_db -> FakeDB
        fake_db = FakeDB(docs=docs or [])
        fake_database_mod = types.ModuleType("database")
        fake_database_mod.get_db = lambda: fake_db
        sys.modules["database"] = fake_database_mod

        sys.modules.pop("main", None)
        mod = importlib.import_module("app.main")
        return mod, fake_db

    return _import



@pytest.fixture
def client_with_docs(import_main_module):
    mod, db = import_main_module(docs=[
        {"_id": "3824077", "title": "flat1"},
        {"_id": "x2", "title": "flat2"},
    ])
    return mod.app.test_client(), mod, db


@pytest.fixture
def client_empty(import_main_module):
    mod, db = import_main_module(docs=[])
    return mod.app.test_client(), mod, db


# ---------------- ТЕСТЫ /apartments/<id> ----------------

def test_apartment_get_401_without_token(client_with_docs):
    client, mod, _ = client_with_docs
    r = client.get("/apartments/3824077")
    assert r.status_code == 401
    assert r.get_json()["error"] == "Token missing"


def test_apartment_get_402_invalid_token(client_with_docs, monkeypatch):
    client, mod, _ = client_with_docs
    # Патчим validate_token в модуле main
    monkeypatch.setattr(mod, "validate_token", lambda t: None)

    r = client.get("/apartments/3824077", headers={"Authorization": "Bearer bad"})
    assert r.status_code == 402
    assert r.get_json()["error"] == "Invalid or expired token"


def test_apartment_get_200_found(client_with_docs, monkeypatch):
    client, mod, _ = client_with_docs
    monkeypatch.setattr(mod, "validate_token", lambda t: {"sub": "user"})  # валидный токен

    r = client.get("/apartments/3824077", headers={"Authorization": "Bearer good"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["_id"] == "3824077"
    assert data["title"] == "flat1"


def test_apartment_get_404_not_found(client_with_docs, monkeypatch):
    client, mod, _ = client_with_docs
    monkeypatch.setattr(mod, "validate_token", lambda t: {"sub": "user"})

    r = client.get("/apartments/unknown", headers={"Authorization": "Bearer good"})
    assert r.status_code == 404
    assert r.get_json()["error"] == "Apartment not found"
