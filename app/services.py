from database import get_apartments_db, get_rental_db
from parsers.realt_apartments_parser import parse_all_apartments_ids_from_realt, parse_apartment_data_from_realt
from parsers.realt_rent_parser import parse_rent_data_from_realt, parse_all_rent_ids_from_realt
from translator import transform_mongo_apartments_to_django, transform_mongo_rent_to_django
import requests


def put_apartments_list_from_realt_to_mongo():
    try:
        with get_apartments_db() as db:
            coll = db.apartments
            parsed_apartments = parse_all_apartments_ids_from_realt()
            if not parsed_apartments:
                print("No new apartments found during parsing")
                return []

            existing_ids = {doc["_id"] for doc in coll.find({}, {"_id": 1})}
            new_apartments = [apt for apt in parsed_apartments if apt.get("_id") not in existing_ids]

            if new_apartments:
                coll.insert_many(new_apartments)

            return new_apartments
    except Exception as e:
        print(f'Database connection error: {e}')
        return []


def put_apartment_info_from_realt_to_mongo():
    try:
        with get_apartments_db() as db:
            coll = db.apartments

            new_apartments = list(coll.find({'state': 'first'}))
            if not new_apartments:
                print("No new apartments to update")
                return None

            updated_count = 0
            for apartment in new_apartments:
                current_id = apartment.get('_id')
                pre_data = parse_apartment_data_from_realt(apartment.get('link'))
                data = transform_mongo_apartments_to_django(pre_data)
                data['state'] = 'second'
                if data:
                    result = coll.update_one(
                        {'_id': current_id},
                        {'$set': data},
                        upsert=True
                    )
                    if result.modified_count > 0:
                        updated_count += 1

            print(f"Updated {updated_count} apartments")
            return updated_count
    except Exception as e:
        print(f'Database connection error: {e}')
        return []


def send_apartments_ids_webhook_to_django():
    try:
        with get_apartments_db() as db:
            coll = db.apartments

            django_webhook_url = 'http://django:8000/apartments-webhook-endpoint/'
            headers = {'Content-Type': 'application/json'}
            new_apartments = [str(apartment.get('_id')) for apartment in coll.find({'state': 'second'})]

            try:
                response = requests.post(
                    django_webhook_url,
                    json={'ids': new_apartments},
                    headers=headers,
                    timeout=10
                )
                response.raise_for_status()
                print('Webhook send successfully to django')
                return new_apartments
            except requests.exceptions.RequestException as e:
                print(f'Error sending webhook to Django: {e}')
                raise
    except Exception as e:
        print(f'Database connection error: {e}')
        return []


def put_rent_list_from_realt_to_mongo():
    try:
        with get_rental_db() as db:
            coll = db.rental
            parsed_rents = parse_all_rent_ids_from_realt()
            if not parsed_rents:
                print("No new apartments found during parsing")
                return []

            existing_ids = {doc["_id"] for doc in coll.find({}, {"_id": 1})}
            new_rents = [rent for rent in parsed_rents if rent.get("_id") not in existing_ids]

            if new_rents:
                coll.insert_many(new_rents)

            return new_rents
    except Exception as e:
        print(f'Database connection error: {e}')
        return []


def put_rent_info_from_realt_to_mongo():
    try:
        with get_rental_db() as db:
            coll = db.rental

            new_rents = list(coll.find({'state': 'first'}))
            if not new_rents:
                print("No new apartments to update")
                return None

            updated_count = 0
            for rent in new_rents:
                current_id = rent.get('_id')
                pre_data = parse_rent_data_from_realt(rent.get('link'))
                data = transform_mongo_rent_to_django(pre_data)
                data['state'] = 'second'
                if data:
                    result = coll.update_one(
                        {'_id': current_id},
                        {'$set': data},
                        upsert=True
                    )
                    if result.modified_count > 0:
                        updated_count += 1

            print(f"Updated {updated_count} apartments")
            return updated_count
    except Exception as e:
        print(f'Database connection error: {e}')
        return []


def send_rent_ids_webhook_to_django():
    try:
        with get_rental_db() as db:
            coll = db.rental

            django_webhook_url = 'http://django:8000/rent-webhook-endpoint/'
            headers = {'Content-Type': 'application/json'}
            new_rents = [str(rent.get('_id')) for rent in coll.find({'state': 'second'})]

            try:
                response = requests.post(
                    django_webhook_url,
                    json={'ids': new_rents},
                    headers=headers,
                    timeout=10
                )
                response.raise_for_status()
                print('Webhook send successfully to django')
                return new_rents
            except requests.exceptions.RequestException as e:
                print(f'Error sending webhook to Django: {e}')
                raise
    except Exception as e:
        print(f'Database connection error: {e}')
        return []


if __name__ == '__main__':
    put_apartment_info_from_realt_to_mongo()
