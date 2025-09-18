import json


def transform_mongo_to_django(mongo_data):
    """
    Переводит русские поля в mongo на английский и подгоняет под структуру API
    """
    DEFAULT_VALUES = {
        # Обязательные поля для Location
        'building.location.street': 'Не указана',
        'building.location.house_number': '0',
        'building.location.town.name': 'Не указан',
        'building.location.town.region.name': 'Не указан',

        # Обязательные поля для Apartment
        'title': 'Без названия',
        'price': 0.0,
        'total_area': 0.0,
        'room_count': 1,
        'description': 'Нет описания',
        'floor': 1,
    }
    # Инициализируем структуру как в API
    django_data = {
        "building": {
            "location": {
                "town": {
                    "region": {
                        "name": DEFAULT_VALUES['building.location.town.region.name']
                    },
                    "name": DEFAULT_VALUES['building.location.town.name']
                },
                "district": "",
                "microdistrict": "",
                "street": DEFAULT_VALUES['building.location.street'],
                "house_number": DEFAULT_VALUES['building.location.house_number'],
                "latitude": None,
                "longitude": None
            },
            "floors_total": None,
            "wall_material": "",
            "construction_year": None,
            "house_amenities": "",
            "parking": ""
        },
        "images": [],
        "title": DEFAULT_VALUES['title'],
        "price": DEFAULT_VALUES['price'],
        "total_area": DEFAULT_VALUES['total_area'],
        "living_area": None,
        "kitchen_area": None,
        "balcony_area": None,
        "balcony": None,
        "room_count": DEFAULT_VALUES['room_count'],
        "description": DEFAULT_VALUES['description'],
        "floor": DEFAULT_VALUES['floor'],
        "sale_conditions": None,
        "bathroom_count": None,
        "ceiling_height": None,
        "renovation": "",
        "condition": "New",
        "contract_number": "",
        "contract_date": None,
        "level_count": None,
        "ownership_type": None,
        "link": ""
    }

    # Разделим маппинг на разные типы полей
    direct_mapping = {
        "title": "title",
        "link": "link",
        "description": "description",
        "contract_number": "Номер договора",
        "renovation": "Ремонт"
    }

    numeric_mapping = {
        "price": ("price", lambda x: float(x.replace(" р.", "").replace(" ", "").replace(",", ".")) if isinstance(mongo_data.get("price"), str) else ("price", float)),
        "total_area": ("Площадь общая", lambda x: float(x.replace(" м²", "").replace(",", "."))),
        "living_area": ("Площадь жилая", lambda x: float(x.replace(" м²", "").replace(",", "."))),
        "kitchen_area": ("Площадь кухни", lambda x: float(x.replace(" м²", "").replace(",", "."))),
        "room_count": ("Количество комнат", int),
        "ceiling_height": ("Высота потолков", lambda x: float(x.replace(" м", "").replace(",", "."))),
        "construction_year": ("Год постройки", int)
    }

    choice_mapping = {
        "balcony": {
            "field": "Балкон",
            "choices": {
                "Лоджия": "Loggia",
                "Балкон": "Classic",
                "Французский балкон": "French",
                "Угловой балкон": "Extended",
                "Нет": "No",
                "Отсутствует": "No"
            },
            'default': 'No'
        },
        "sale_conditions": {
            "field": "Условия продажи",
            "choices": {
                "Чистая продажа": "Open",
                "Свободная продажа": "Open",
                "Альтернативная": "Alternative",
                "Альтернатива": "Alternative",
                "Условная": "Condition",
                "С условием": "Condition"
            },
            'default': 'Open'
        },
        "condition": {
            "field": "Состояние",
            "choices": {
                "Новостройка": "New",
                "С ремонтом": "Almost",
                "Хорошее": "Good",
                "Удовлетворительное": "Fair",
                "Требует ремонта": "Renovation",
                "Аварийное": "Uninhabitable"
            },
            'default': 'New'
        },
        "ownership_type": {
            "field": "Собственность",
            "choices": {
                "Частная": "Private",
                "Приватная": "Private",
                "Государственная": "State",
                "Гос.": "State",
                "Совместная": "Joint",
                "Долевая": "Shared",
                "Коллективная": "Collective",
                "Иностранная": "Foreign"
            },
            'default': 'Private'
        },
        "wall_material": {
            "field": "Тип дома",
            "choices": {
                "Панельный": "Panel",
                "Кирпичный": "Brick",
                "Монолитный": "Monolithic",
                "Блочный": "Block"
            },
            'default': 'Panel'
        }
    }

    # Обрабатываем прямые поля
    for django_field, mongo_field in direct_mapping.items():
        if mongo_field in mongo_data:
            django_data[django_field] = str(mongo_data[mongo_field])

    # Обрабатываем числовые поля
    for django_field, (mongo_field, converter) in numeric_mapping.items():
        if mongo_field in mongo_data:
            try:
                value = converter(mongo_data[mongo_field])
                if django_field == "construction_year":
                    # поле вложенное
                    django_data["building"]["construction_year"] = value
                else:
                    django_data[django_field] = value
            except (ValueError, TypeError, AttributeError):
                pass

    # Обрабатываем выборные поля
    for django_field, config in choice_mapping.items():
        mongo_field = config["field"]
        if mongo_field in mongo_data:
            value = mongo_data[mongo_field]
            mapped = config["choices"].get(value, config["default"])
            if django_field == "wall_material":
                # кладём в нужное вложенное поле
                django_data["building"]["wall_material"] = mapped
            else:
                django_data[django_field] = mapped

    # Обрабатываем этажи
    if "Этаж / этажность" in mongo_data:
        try:
            floor, floors_total = [x.strip() for x in mongo_data["Этаж / этажность"].split("/")]
            django_data["floor"] = int(floor)
            django_data["building"]["floors_total"] = int(floors_total)
        except (ValueError, AttributeError):
            pass

    # Обрабатываем координаты
    if "Координаты" in mongo_data:
        try:
            coords = mongo_data["Координаты"].split(",")
            if len(coords) == 2:
                lat, lon = [x.strip() for x in coords]
                django_data["building"]["location"]["latitude"] = float(lat)
                django_data["building"]["location"]["longitude"] = float(lon)
        except (ValueError, AttributeError):
            pass

    # Заполняем адресные данные
    address_fields = {
        "building.location.town.region.name": ["Область", "Обл.", "Регион"],
        "building.location.town.name": ["Населенный пункт", "Город", "г."],
        "building.location.district": ["Район", "Р-н"],
        "building.location.street": ["Улица", "ул.", "Адрес"],
        "building.location.house_number": ["Дом", "Номер дома", "№ дома"]
    }

    for path, mongo_fields in address_fields.items():
        for field in mongo_fields:
            if field in mongo_data:
                # Устанавливаем значение по пути в структуре
                keys = path.split('.')
                current = django_data
                for key in keys[:-1]:
                    current = current.setdefault(key, {})
                current[keys[-1]] = str(mongo_data[field])
                break

    return django_data


if __name__ == "__main__":
    mongo_data = {
  "_id": "3824077",
  "link": "https://realt.by/grodno-region/sale-flats/object/3824077/",
  "price": "277 770 р.",
  "title": "Купить 3-комнатную квартиру, г. Гродно, ул. Лидская, 33",
  "Балкон": "Лоджия",
  "Вид из окон": "Во двор, На улицу",
  "Год постройки": "2019",
  "Количество комнат": "3",
  "Координаты": "53.6673, 23.8516",
  "Населенный пункт": "г. Гродно",
  "Номер дома": "33",
  "Область": "Гродненская область",
  "Площадь жилая": "74 м²",
  "Площадь общая": "78 м²",
  "Раздельных комнат": "3",
  "Тип дома": "Панельный",
  "Район": "Гродненский район",
  "Район города": "Октябрьский район",
  "Ремонт": "Евроремонт",
  "Санузел": "Раздельный",
  "Собственность": "Частная",
  "Стоянка автомобиля": "Есть",
  "Улица": "Лидская ул.",
  "Условия продажи": "Чистая продажа",
  "Этаж / этажность": "6 / 7"
}

    django_data = transform_mongo_to_django(mongo_data)
    print(json.dumps(django_data, ensure_ascii=False, indent=2))
