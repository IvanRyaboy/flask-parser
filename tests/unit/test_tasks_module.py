import importlib
import sys
import types

import pytest


@pytest.fixture(autouse=True)
def no_autodiscover(monkeypatch):
    import celery as celery_pkg
    monkeypatch.setattr(celery_pkg.Celery, "autodiscover_tasks", lambda *a, **k: None)


@pytest.fixture
def app_celery_module(no_autodiscover):
    sys.modules.pop("app_celery", None)
    mod = importlib.import_module("app.app_celery")
    mod.celery.conf.task_always_eager = True
    return mod


@pytest.fixture
def tasks_module(app_celery_module):
    sys.modules.pop("tasks", None)
    mod = importlib.import_module("app.tasks")
    return mod


def test_parse_apartment_list_success(tasks_module, monkeypatch, caplog):
    monkeypatch.setattr(tasks_module, "put_apartments_list_from_realt_to_mongo",
                        lambda: [{"_id": "1"}, {"_id": "2"}])

    caplog.set_level("INFO")
    res = tasks_module.parse_apartment_list.run()

    assert res == {"status": "success", "count": 2}
    assert any("Начало парсинга списка квартир" in r.message for r in caplog.records)
    assert any("Успешно спаршено 2 квартир" in r.message for r in caplog.records)


def test_parse_apartment_list_retry_on_error(tasks_module, monkeypatch, caplog):
    monkeypatch.setattr(
        tasks_module,
        "put_apartments_list_from_realt_to_mongo",
        lambda: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    task = tasks_module.parse_apartment_list
    called = {}

    def fake_retry(*args, **kwargs):
        called["kwargs"] = kwargs
        raise RuntimeError("retry-called")

    monkeypatch.setattr(task, "retry", fake_retry, raising=True)

    caplog.set_level("ERROR")
    with pytest.raises(RuntimeError, match="retry-called"):
        task.run()  # без аргументов

    assert called["kwargs"].get("countdown") == 60
    assert called["kwargs"].get("max_retries") == 3
    assert isinstance(called["kwargs"].get("exc"), RuntimeError)
    assert any("Ошибка парсинга списка: boom" in r.message for r in caplog.records)


def test_parse_apartment_details_success(tasks_module, monkeypatch, caplog):
    monkeypatch.setattr(tasks_module, "put_apartment_info_from_realt_to_mongo",
                        lambda: 5)

    caplog.set_level("INFO")
    res = tasks_module.parse_apartment_details.run()
    assert res == {"status": "success", "details_processed": 5}
    assert any("Начало парсинга деталей квартир" in r.message for r in caplog.records)
    assert any("Успешно обработано 5 деталей квартир" in r.message for r in caplog.records)


def test_parse_apartment_details_retry_on_error(tasks_module, monkeypatch, caplog):
    monkeypatch.setattr(
        tasks_module,
        "put_apartment_info_from_realt_to_mongo",
        lambda: (_ for _ in ()).throw(RuntimeError("oops")),
    )

    task = tasks_module.parse_apartment_details
    called = {}

    def fake_retry(*args, **kwargs):
        called["kwargs"] = kwargs
        raise RuntimeError("retry-called")

    monkeypatch.setattr(task, "retry", fake_retry, raising=True)

    caplog.set_level("ERROR")
    with pytest.raises(RuntimeError, match="retry-called"):
        task.run()  # без аргументов

    assert called["kwargs"].get("countdown") == 60
    assert called["kwargs"].get("max_retries") == 3
    assert isinstance(called["kwargs"].get("exc"), RuntimeError)
    assert any("Ошибка парсинга деталей: oops" in r.message for r in caplog.records)


def test_send_webhook_to_django_success(tasks_module, monkeypatch, caplog):
    monkeypatch.setattr(tasks_module, "send_ids_webhook_to_django",
                        lambda: ["1", "2", "3"])

    caplog.set_level("INFO")
    res = tasks_module.send_webhook_to_django.run()
    assert res == {"status": "success", "ids_sent": ["1", "2", "3"], "count": 3}
    assert any("Sending apartment IDs to Django webhook" in r.message for r in caplog.records)


def test_send_webhook_to_django_retry_on_error(tasks_module, monkeypatch, caplog):
    monkeypatch.setattr(
        tasks_module,
        "send_ids_webhook_to_django",
        lambda: (_ for _ in ()).throw(RuntimeError("net")),
    )

    task = tasks_module.send_webhook_to_django
    called = {}

    def fake_retry(*args, **kwargs):
        called["args"] = args
        called["kwargs"] = kwargs
        raise RuntimeError("retry-called")

    monkeypatch.setattr(task, "retry", fake_retry, raising=True)

    caplog.set_level("ERROR")

    with pytest.raises(RuntimeError, match="retry-called"):
        task.run()

    assert "kwargs" in called and isinstance(called["kwargs"].get("exc"), RuntimeError)
    assert any("Error in send_webhook_to_django task: net" in r.message for r in caplog.records)


