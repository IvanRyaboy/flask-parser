# tests/conftest.py
import sys
import types
import importlib

import mongomock
import pytest


# ----------------- БАЗОВАЯ ИЗОЛЯЦИЯ ОКРУЖЕНИЯ -----------------

@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    # Минимизируем влияние локальных .env/переменных
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.setenv("PYTHONHASHSEED", "0")
    # Значения, которые читает app.py через os.getenv (если нужно)
    monkeypatch.setenv("LWKS_URL", "http://jwks.invalid/.well-known/jwks.json")
    monkeypatch.setenv("AUDIENCE", "test-aud")
    monkeypatch.setenv("ISSUER", "https://issuer.test")


# ----------------- MONGO: mongomock + get_apartments_db -----------------

@pytest.fixture
def mongo_db():
    """Изолированная in-memory БД для тестов."""
    return mongomock.MongoClient()["testdb"]


@pytest.fixture
def patch_database_get_db(monkeypatch, mongo_db):
    """
    Патчим реальный модуль database.get_apartments_db, чтобы код приложения
    работал с mongomock.
    """
    # Если модуль уже импортирован – патчим его.
    try:
        database = importlib.import_module("database")
        monkeypatch.setattr(database, "get_apartments_db", lambda: mongo_db, raising=True)
    except ModuleNotFoundError:
        # Иначе подсовываем фиктивный модуль до импорта приложения.
        fake_database = types.ModuleType("database")
        fake_database.get_db = lambda: mongo_db
        sys.modules["database"] = fake_database
    yield


# --------- fake_useragent: стабильный UserAgent().random ---------

@pytest.fixture(autouse=True)
def patch_fake_useragent(monkeypatch):
    """
    realt_parser использует fake_useragent.UserAgent().random.
    Фиксируем значение, чтобы тесты не ходили в сеть.
    """
    try:
        import parsers.realt_parser as rp
        class _UA:
            random = "UnitTestAgent/1.0"
        monkeypatch.setattr(rp.fake_useragent, "UserAgent", lambda: _UA(), raising=True)
    except ModuleNotFoundError:
        # Тесты, где парсер не используется, спокойно пройдут без патча.
        pass
    yield


# ----------------- Flask app: безопасный импорт -----------------

@pytest.fixture
def app_module(patch_database_get_db, monkeypatch):
    """
    Импортирует app.py безопасно:
    - отключает Flask.run() на случай прямого вызова в модуле;
    - возвращает сам модуль (для доступа к app/test_client).
    """
    # Не позволяем app.run() запуститься при импорте
    import flask.app
    monkeypatch.setattr(flask.app.Flask, "run", lambda self, *a, **k: None, raising=True)

    # Чистый импорт модуля приложения
    sys.modules.pop("app", None)
    mod = importlib.import_module("app")
    return mod


@pytest.fixture
def client(app_module):
    """Flask test client."""
    return app_module.app.test_client()


# ----------------- Celery: eager-режим для юнит/интеграций -----------------

@pytest.fixture
def celery_app(monkeypatch):
    """
    Импортирует app_celery и переводит Celery в eager-режим,
    чтобы tasks.delay() выполнялись синхронно без Redis.
    Также отключаем autodiscover, чтобы избежать циклов при тестах tasks.py.
    """
    # Отключаем autodiscover на время импорта конфигурации
    import celery as celery_pkg
    monkeypatch.setattr(celery_pkg.Celery, "autodiscover_tasks", lambda *a, **k: None, raising=True)

    sys.modules.pop("app_celery", None)
    app_celery = importlib.import_module("app_celery")
    app_celery.celery.conf.task_always_eager = True
    return app_celery


@pytest.fixture
def tasks_module(celery_app):
    """
    Импортирует tasks.py после настройки Celery.
    Возвращает сам модуль с регистрированными задачами.
    """
    sys.modules.pop("tasks", None)
    return importlib.import_module("tasks")
