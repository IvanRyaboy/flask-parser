import sys
import types
import importlib
from celery.schedules import crontab as crontab_cls
import pytest


@pytest.fixture(autouse=True)
def fake_tasks_module(monkeypatch):
    fake = types.ModuleType("tasks")
    sys.modules["tasks"] = fake
    try:
        yield
    finally:
        sys.modules.pop("tasks", None)


@pytest.fixture
def app_celery_module(fake_tasks_module):
    sys.modules.pop("app_celery", None)
    mod = importlib.import_module("app.app_celery")
    return mod


def test_celery_basic_config(app_celery_module):
    celery = app_celery_module.celery

    assert celery.main == "app_celery"

    assert celery.conf.broker_url == "redis://redis:6379/0"
    assert celery.conf.result_backend == "redis://redis:6379/0"

    assert celery.conf.timezone == "UTC"
    assert celery.conf.enable_utc is True


def _assert_crontab_at(cr, *, hour: int, minute: int):
    if hasattr(cr, "minute") and hasattr(cr, "hour") and isinstance(cr, crontab_cls):
        try:
            assert set(cr.minute) == {minute}
            assert set(cr.hour) == {hour}
            return
        except TypeError:
            pass
    orig_min = getattr(cr, "_orig_minute", None)
    orig_hour = getattr(cr, "_orig_hour", None)
    if orig_min is not None and orig_hour is not None:
        assert str(orig_min) == str(minute)
        assert str(orig_hour) == str(hour)
        return
    s = str(cr)
    assert f"minute={minute}" in s and f"hour={hour}" in s


def test_beat_schedule_exists_and_valid(app_celery_module):
    celery = app_celery_module.celery
    schedule = celery.conf.beat_schedule

    assert "first_parse_every_1_hour" in schedule
    assert "second_parse_a_day" in schedule
    assert "send_webhooks_once_a_day" in schedule

    hourly = schedule["first_parse_every_1_hour"]
    assert hourly["task"] == "tasks.parse_apartment_list"
    assert isinstance(hourly["schedule"], (int, float))
    assert hourly["schedule"] == 3600.0

    from celery.schedules import crontab as crontab_cls
    second = schedule["second_parse_a_day"]
    sendwh = schedule["send_webhooks_once_a_day"]

    assert second["task"] == "tasks.parse_apartment_details"
    assert sendwh["task"] == "tasks.send_webhook_to_django"
    assert isinstance(second["schedule"], crontab_cls)
    assert isinstance(sendwh["schedule"], crontab_cls)

    _assert_crontab_at(second["schedule"], hour=12, minute=0)
    _assert_crontab_at(sendwh["schedule"], hour=13, minute=0)


def test_autodiscover_does_not_crash_on_import(app_celery_module):
    assert hasattr(app_celery_module, "celery")
