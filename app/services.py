from database import get_apartments_db
from parsers.realt_parser import parse_all_apartments_ids_from_realt, parse_apartment_data_from_realt
from bson import ObjectId
from translator import transform_mongo_to_django
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
        data = transform_mongo_to_django(pre_data)
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


def send_ids_webhook_to_django():
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