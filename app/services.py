from app.database import get_db
from parsers.realt_parser import parse_all_apartments_ids_from_realt, parse_apartment_data_from_realt
from bson import ObjectId


def put_apartments_list_from_realt_to_mongo():
    db = get_db()
    coll = db.apartments
    last_apartment = coll.find_one(sort=[('_id', -1)]) if coll is not None else None
    parsed_apartments = parse_all_apartments_ids_from_realt()

    new_apartments = []

    if not last_apartment:
        coll.insert_many(parsed_apartments)
        for apartment in parsed_apartments:
            new_apartments.append(apartment)
        return new_apartments

    last_apartment_id = last_apartment.get('_id') or str(last_apartment.get('_id'))

    for apartment in parsed_apartments:
        current_id = apartment.get('_id')
        if current_id == last_apartment_id:
            coll.insert_many(new_apartments)
            return new_apartments
        new_apartments.append(apartment)

    coll.insert_many(new_apartments)
    return new_apartments


def put_apartment_info_from_realt_to_mongo():
    db = get_db()
    coll = db.apartments

    new_apartments = put_apartments_list_from_realt_to_mongo()
    print(new_apartments)

    for apartment in new_apartments:
        current = {'_id': apartment.get('_id') or str(apartment.get('_id'))}
        data = parse_apartment_data_from_realt(apartment.get('link'))
        print(data)
        new_data = {"$set": data}
        coll.update_one(current, new_data)


if __name__ == '__main__':
    print(put_apartment_info_from_realt_to_mongo())
