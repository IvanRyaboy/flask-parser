from celery import Celery
from celery.schedules import crontab
import os

celery = Celery(
    'app_celery',
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/0',
)
celery.autodiscover_tasks(['tasks'])

celery.conf.update(
    timezone='UTC',
    enable_utc=True,
    beat_schedule={
        'first_parse_every_1_hour': {
            'task': 'tasks.parse_apartment_list',
            'schedule': 3600.0,
        },
        'second_parse_a_day': {
            'task': 'tasks.parse_apartment_details',
            'schedule': crontab(hour=12, minute=0),
        },
        'send_webhooks_once_a_day': {
            'task': 'tasks.send_webhook_to_django',
            'schedule': crontab(hour=13, minute=0),
        }
    }
)