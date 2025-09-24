from database import get_apartments_db, get_rental_db
from parsers.realt_apartments_parser import parse_all_apartments_ids_from_realt, parse_apartment_data_from_realt
from parsers.realt_rent_parser import parse_rent_data_from_realt, parse_all_rent_ids_from_realt
from bson import ObjectId
from translator import transform_mongo_apartments_to_django, transform_mongo_rent_to_django
import requests


def put_apartments_list_from_realt_to_mongo():
    try:
        db = get_apartments_db()
        coll = db.apartments
    except Exception as e:
        print(f'Database connection error: {e}')
        return []
    last_apartment = coll.find_one(sort=[('_id', -1)]) if coll.count_documents({}) > 0 else None
    parsed_apartments = parse_all_apartments_ids_from_realt()

    if not parsed_apartments:
        print("No new apartments found during parsing")
        return []

    new_apartments = []

    if not last_apartment:
        coll.insert_many(reversed(parsed_apartments))
        return parsed_apartments

    last_apartment_id = last_apartment.get('_id')

    for apartment in parsed_apartments:
        current_id = apartment.get('_id')
        if current_id == last_apartment_id:
            break
        new_apartments.append(apartment)

    if new_apartments:
        coll.insert_many(new_apartments)

    return new_apartments


def put_apartment_info_from_realt_to_mongo():
    try:
        db = get_apartments_db()
        coll = db.apartments
    except Exception as e:
        print(f'Database connection error: {e}')
        return []

    new_apartments = []

    for apartment in coll.find({'state': 'first'}):
        new_apartments.append(apartment)

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


def send_apartments_ids_webhook_to_django():
    try:
        db = get_apartments_db()
        coll = db.apartments
    except Exception as e:
        print(f'Database connection error: {e}')
        return []

    django_webhook_url = 'http://django:8000/webhook-endpoint/'
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


def put_rent_list_from_realt_to_mongo():
    try:
        db = get_rental_db()
        coll = db.rental
    except Exception as e:
        print(f'Database connection error: {e}')
        return []
    last_rent = coll.find_one(sort=[('_id', -1)]) if coll.count_documents({}) > 0 else None
    parsed_rents = parse_all_rent_ids_from_realt()

    if not parsed_rents:
        print("No new apartments found during parsing")
        return []

    new_rents = []

    if not last_rent:
        coll.insert_many(reversed(parsed_rents))
        return parsed_rents

    last_rent_id = last_rent.get('_id')

    for rent in parsed_rents:
        current_id = rent.get('_id')
        if current_id == last_rent_id:
            break
        new_rents.append(rent)

    if new_rents:
        coll.insert_many(new_rents)

    return new_rents


def put_rent_info_from_realt_to_mongo():
    try:
        db = get_rental_db()
        coll = db.rental
    except Exception as e:
        print(f'Database connection error: {e}')
        return []

    new_rents = []

    for rent in coll.find({'state': 'first'}):
        new_rents.append(rent)

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


def send_rent_ids_webhook_to_django():
    try:
        db = get_apartments_db()
        coll = db.apartments
    except Exception as e:
        print(f'Database connection error: {e}')
        return []

    django_webhook_url = 'http://django:8000/webhook-endpoint/'
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


if __name__ == '__main__':
    put_apartment_info_from_realt_to_mongo()