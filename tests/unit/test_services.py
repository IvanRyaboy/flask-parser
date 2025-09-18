import pytest
import types

import app.services as srv


class FakeUpdateResult:
    def __init__(self, modified_count: int):
        self.modified_count = modified_count


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = list(docs or [])

    def count_documents(self, q):
        return len(self.docs)

    def find_one(self, sort=None):
        if not self.docs:
            return None
        if sort:
            key, direction = sort[0]
            rev = direction < 0

            def _key(d):
                v = d.get(key)
                try:
                    return int(v)
                except Exception:
                    return v
            return sorted(self.docs, key=_key, reverse=rev)[0]
        return self.docs[0]

    def insert_many(self, docs):
        self.docs.extend(docs)

    def find(self, q):
        if not q:
            return list(self.docs)
        out = []
        for d in self.docs:
            ok = True
            for k, v in q.items():
                if d.get(k) != v:
                    ok = False
                    break
            if ok:
                out.append(d)
        return out

    def update_one(self, flt, update, upsert=False):
        _id = flt.get("_id")
        idx = next((i for i, d in enumerate(self.docs) if d.get("_id") == _id), None)
        new_values = update.get("$set", {})
        if idx is None:
            if upsert:
                doc = {"_id": _id, **new_values}
                self.docs.append(doc)
                return FakeUpdateResult(modified_count=1)
            return FakeUpdateResult(modified_count=0)
        before = dict(self.docs[idx])
        self.docs[idx].update(new_values)
        modified = int(before != self.docs[idx])
        return FakeUpdateResult(modified_count=modified)


class FakeDB:
    def __init__(self, docs=None):
        self.apartments = FakeCollection(docs=docs or [])


@pytest.fixture
def fake_db(monkeypatch):
    db = FakeDB()
    monkeypatch.setattr(srv, "get_db", lambda: db)
    return db


@pytest.fixture
def patch_parsers(monkeypatch):
    """Хелпер для подмены парсеров в конкретных тестах."""
    def _set(ids=None, details=None):
        if ids is not None:
            monkeypatch.setattr(
                srv, "parse_all_apartments_ids_from_realt",
                lambda: ids
            )
        if details is not None:
            monkeypatch.setattr(
                srv, "parse_apartment_data_from_realt",
                lambda url: details
            )
    return _set


@pytest.fixture
def patch_translator(monkeypatch):
    def _set(value):
        monkeypatch.setattr(srv, "transform_mongo_to_django", lambda doc: dict(value))
    return _set


def test_put_apartments_list_first_import_inserts_all(fake_db, patch_parsers):
    parsed = [{"_id": "10", "state": "first"}, {"_id": "11", "state": "first"}]
    patch_parsers(ids=parsed)
    out = srv.put_apartments_list_from_realt_to_mongo()
    assert out == parsed
    assert fake_db.apartments.count_documents({}) == 2


def test_put_apartments_list_no_new_ids_returns_empty(fake_db, patch_parsers):
    fake_db.apartments.insert_many([{"_id": "20", "state": "first"}])
    patch_parsers(ids=[{"_id": "20", "state": "first"}])

    out = srv.put_apartments_list_from_realt_to_mongo()
    assert out == []
    assert fake_db.apartments.count_documents({}) == 1


def test_put_apartments_list_stops_at_last_apartment_and_inserts_new(fake_db, patch_parsers):
    fake_db.apartments.insert_many([{"_id": "100", "state": "first"}])
    patch_parsers(ids=[
        {"_id": "101", "state": "first"},
        {"_id": "100", "state": "first"},
        {"_id": "99", "state": "first"},
    ])

    out = srv.put_apartments_list_from_realt_to_mongo()
    assert out == [{"_id": "101", "state": "first"}]
    assert any(d["_id"] == "101" for d in fake_db.apartments.docs)
    assert not any(d["_id"] == "99" for d in fake_db.apartments.docs)


def test_put_apartments_list_when_parser_returns_empty(fake_db, patch_parsers, capsys):
    patch_parsers(ids=[])
    out = srv.put_apartments_list_from_realt_to_mongo()
    assert out == []
    captured = capsys.readouterr().out
    assert "No new apartments found during parsing" in captured


def test_put_apartments_list_db_error_returns_empty(monkeypatch, capsys):
    monkeypatch.setattr(srv, "get_db", lambda: (_ for _ in ()).throw(RuntimeError("db down")))
    out = srv.put_apartments_list_from_realt_to_mongo()
    assert out == []
    assert "Database connection error" in capsys.readouterr().out


def test_put_apartment_info_updates_first_state_docs(fake_db, patch_parsers, patch_translator, capsys):
    fake_db.apartments.insert_many([
        {"_id": "1", "link": "http://x/1", "state": "first"},
        {"_id": "2", "link": "http://x/2", "state": "first"},
        {"_id": "3", "link": "http://x/3", "state": "second"},
    ])

    patch_parsers(details={"raw": True})
    patch_translator({"title": "ok", "price": "100 $"})

    updated = srv.put_apartment_info_from_realt_to_mongo()
    assert updated == 2

    docs = {d["_id"]: d for d in fake_db.apartments.docs}
    assert docs["1"]["state"] == "second" and docs["1"]["title"] == "ok"
    assert docs["2"]["state"] == "second" and docs["2"]["price"] == "100 $"
    assert docs["3"]["state"] == "second"

    assert "Updated 2 apartments" in capsys.readouterr().out


def test_put_apartment_info_no_first_docs_returns_none(fake_db, patch_parsers, patch_translator, capsys):
    fake_db.apartments.insert_many([
        {"_id": "10", "link": "http://x/10", "state": "second"}
    ])
    patch_parsers(details={"raw": True})
    patch_translator({"t": "v"})

    out = srv.put_apartment_info_from_realt_to_mongo()
    assert out is None
    assert "No new apartments to update" in capsys.readouterr().out


def test_put_apartment_info_db_error_returns_empty(monkeypatch, capsys):
    monkeypatch.setattr(srv, "get_db", lambda: (_ for _ in ()).throw(RuntimeError("db down")))
    out = srv.put_apartment_info_from_realt_to_mongo()
    assert out == []
    assert "Database connection error" in capsys.readouterr().out


class DummyResponseOK:
    status_code = 200

    def raise_for_status(self):
        return None


def test_send_ids_webhook_posts_ids_and_returns_list(fake_db, monkeypatch):
    fake_db.apartments.insert_many([
        {"_id": "1", "state": "second"},
        {"_id": "2", "state": "first"},
        {"_id": "3", "state": "second"},
    ])

    captured = {}

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return DummyResponseOK()

    monkeypatch.setattr(srv.requests, "post", fake_post)

    out = srv.send_ids_webhook_to_django()
    assert out == ["1", "3"]
    assert captured["url"] == "http://django:8000/webhook-endpoint/"
    assert captured["json"] == {"ids": ["1", "3"]}
    assert captured["headers"]["Content-Type"] == "application/json"
    assert captured["timeout"] == 10


def test_send_ids_webhook_db_error_returns_empty(monkeypatch, capsys):
    monkeypatch.setattr(srv, "get_db", lambda: (_ for _ in ()).throw(RuntimeError("db down")))
    out = srv.send_ids_webhook_to_django()
    assert out == []
    assert "Database connection error" in capsys.readouterr().out
