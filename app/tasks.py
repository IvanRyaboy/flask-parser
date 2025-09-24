from app_celery import celery
from services import *
import logging


logger = logging.getLogger(__name__)


@celery.task(name='tasks.parse_apartment_list', bind=True)
def parse_apartment_list(self):
    """
    Запуск парсинга всего списка квартир
    """
    try:
        logger.info("Начало парсинга списка квартир")
        result = put_apartments_list_from_realt_to_mongo()
        logger.info(f"Успешно спаршено {len(result)} квартир")
        return {'status': 'success', 'count': len(result)}
    except Exception as e:
        logger.error(f"Ошибка парсинга списка: {str(e)}")
        self.retry(exc=e, countdown=60, max_retries=3)


@celery.task(name='tasks.parse_apartment_details', bind=True)
def parse_apartment_details(self):
    """
    Запуск парсинга деталей отдельной квартиры
    """
    try:
        logger.info("Начало парсинга деталей квартир")
        result = put_apartment_info_from_realt_to_mongo()
        logger.info(f"Успешно обработано {result} деталей квартир")
        return {'status': 'success', 'details_processed': result}
    except Exception as e:
        logger.error(f"Ошибка парсинга деталей: {str(e)}")
        self.retry(exc=e, countdown=60, max_retries=3)


@celery.task(name='tasks.send_apartments_webhook_to_django', bind=True)
def send_apartments_webhook_to_django(self):
    """
    Отправляет вебхук на сервис Django
    """
    try:
        logger.info("Sending apartment IDs to Django webhook")
        result = send_apartments_ids_webhook_to_django()
        return {
            'status': 'success',
            'ids_sent': result,
            'count': len(result)
        }
    except Exception as e:
        logger.error(f"Error in send_webhook_to_django task: {str(e)}")
        raise self.retry(exc=e)


@celery.task(name='tasks.parse_rent_list', bind=True)
def parse_rent_list(self):
    """
    Запуск парсинга всего списка арендных квартир
    """
    try:
        logger.info("Начало парсинга списка арендных квартир")
        result = put_rent_list_from_realt_to_mongo()
        logger.info(f"Успешно спаршено {len(result)} арендных квартир")
        return {'status': 'success', 'count': len(result)}
    except Exception as e:
        logger.error(f"Ошибка парсинга списка: {str(e)}")
        self.retry(exc=e, countdown=60, max_retries=3)


@celery.task(name='tasks.parse_rent_details', bind=True)
def parse_rent_details(self):
    """
    Запуск парсинга деталей отдельной арендной квартиры
    """
    try:
        logger.info("Начало парсинга деталей арендных квартир")
        result = put_rent_info_from_realt_to_mongo()
        logger.info(f"Успешно обработано {result} деталей арендных квартир")
        return {'status': 'success', 'details_processed': result}
    except Exception as e:
        logger.error(f"Ошибка парсинга деталей: {str(e)}")
        self.retry(exc=e, countdown=60, max_retries=3)


@celery.task(name='tasks.send_rent_webhook_to_django', bind=True)
def send_rent_webhook_to_django(self):
    """
    Отправляет вебхук на сервис Django
    """
    try:
        logger.info("Sending rent IDs to Django webhook")
        result = send_rent_ids_webhook_to_django()
        return {
            'status': 'success',
            'ids_sent': result,
            'count': len(result)
        }
    except Exception as e:
        logger.error(f"Error in send_webhook_to_django task: {str(e)}")
        raise self.retry(exc=e)
