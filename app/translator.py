import json


def transform_mongo_apartments_to_django(mongo_data):
    """
    Переводит русские поля коллекции Apartments в mongo на английский и подгоняет под структуру API
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


def transform_mongo_rent_to_django(mongo_data):
    """
    Переводит русские поля коллекции Apartments в mongo на английский и подгоняет под структуру API
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

            "balcony": False,
            "floor": DEFAULT_VALUES['floor'],

            "description": DEFAULT_VALUES['description'],

            "room_count": DEFAULT_VALUES['room_count'],
            "separate_rooms": None,

            "renovation": "",
            "furniture": True,
            "bathroom": None,

            "quarter": None,
            "term_of_rent": None,
            "contract_number": "",
            "rent_conditions": None,
            "prepayment": None,

            "parking": False,
            "layout": None
    }

    # ----- Прямые поля (строки без преобразований) -----
    direct_mapping = {
        "title": "title",
        "description": "description",
        "contract_number": "Номер договора",
        "renovation": "Ремонт",  # в rent это произвольная строка — просто прокидываем
        "layout": "Планировка",
        "link": "link",
    }

    # ----- Числовые поля -----
    def _to_float(s: str, repl: tuple[str, ...] = ()) -> float:
        if s is None:
            raise TypeError
        v = str(s)
        for r in repl:
            v = v.replace(r, "")
        v = v.replace(",", ".").strip()
        return float(v)

    numeric_mapping = {
        "price": (
            "price",
            lambda x: _to_float(x, (" р.", "₽", " ",)) if isinstance(x, (str, bytes)) else float(x)
        ),
        "total_area": ("Площадь общая", lambda x: _to_float(x, (" м²",))),
        "living_area": ("Площадь жилая", lambda x: _to_float(x, (" м²",))),
        "kitchen_area": ("Площадь кухни", lambda x: _to_float(x, (" м²",))),
        "room_count": ("Количество комнат", int),
        "separate_rooms": ("Изолированные комнаты", int),  # если источник называет иначе — добавьте синоним внизу
        "quarter": ("Квартал", lambda x: float(str(x).split()[0])),  # берём первое число из "2 кв. 2025"
        "construction_year": ("Год постройки", int)  # уйдёт во вложенное building.construction_year
    }

    # ----- Выборные/булевы поля -----
    choice_mapping = {
        # Балкон в rent — булево
        "balcony": {
            "field": "Балкон",
            "choices": {
                "Балкон": True,
                "Лоджия": True,
                "Французский балкон": True,
                "Угловой балкон": True,
                "Есть": True,
                "Да": True,
                "Нет": False,
                "Отсутствует": False
            },
            "default": False
        },

        # Санузел — нормализуем в короткие коды
        "bathroom": {
            "field": "Санузел",
            "choices": {
                "Совмещенный": "combined",
                "Раздельный": "separate",
                "Два и более": "multiple",
                "Несколько": "multiple",
            },
            "default": None
        },

        # Мебель — булево
        "furniture": {
            "field": "Мебель",
            "choices": {
                "Есть": True,
                "Да": True,
                "Нет": False,
                "Отсутствует": False
            },
            "default": True
        },

        # Срок аренды
        "term_of_rent": {
            "field": "Срок аренды",
            "choices": {
                "Посуточно": "daily",
                "Краткосрочная": "short",
                "Короткий срок": "short",
                "Длительная": "long",
                "Длительный срок": "long",
                "Долгосрочная": "long",
                "Ежемесячно": "monthly"
            },
            "default": None
        },

        # Условия аренды — сводим к кодам (множественность можно обрабатывать вне этого словаря)
        "rent_conditions": {
            "field": "Условия аренды",
            "choices": {
                "Можно с детьми": "kids_ok",
                "Можно с животными": "pets_ok",
                "Нельзя с животными": "no_pets",
                "КУ включены": "utilities_included",
                "Коммунальные включены": "utilities_included",
                "Оплата по счётчикам": "utilities_separate",
            },
            "default": None
        },

        # Предоплата
        "prepayment": {
            "field": "Предоплата",
            "choices": {
                "1 месяц": "1_month",
                "2 месяца": "2_months",
                "100%": "100_percent",
                "Без предоплаты": "no_prepayment"
            },
            "default": None
        },

        # Парковка в rent — булево
        "parking": {
            "field": "Парковка",
            "choices": {
                "Есть": True,
                "Да": True,
                "Нет": False,
                "Отсутствует": False
            },
            "default": False
        },

        # Материал стен — остаётся во вложенном building.wall_material
        "wall_material": {
            "field": "Тип дома",
            "choices": {
                "Панельный": "Panel",
                "Кирпичный": "Brick",
                "Монолитный": "Monolithic",
                "Блочный": "Block"
            },
            "default": "Panel"
        }
    }

    # ----- Обработка прямых полей -----
    for django_field, mongo_field in direct_mapping.items():
        if mongo_field in mongo_data:
            django_data[django_field] = str(mongo_data[mongo_field])

    # ----- Обработка числовых полей -----
    for django_field, (mongo_field, converter) in numeric_mapping.items():
        if mongo_field in mongo_data:
            try:
                value = converter(mongo_data[mongo_field])
                if django_field == "construction_year":
                    # вложенное поле
                    django_data.setdefault("building", {}).setdefault("construction_year", value)
                    django_data["building"]["construction_year"] = value
                else:
                    django_data[django_field] = value
            except (ValueError, TypeError, AttributeError):
                pass

    # ----- Обработка выборных/булевых полей -----
    for django_field, config in choice_mapping.items():
        mongo_field = config["field"]
        if mongo_field in mongo_data:
            raw_value = mongo_data[mongo_field]
            mapped = config["choices"].get(raw_value, config["default"])

            if django_field == "wall_material":
                django_data.setdefault("building", {})["wall_material"] = mapped
            else:
                django_data[django_field] = mapped

    # ----- Этаж / этажность -----
    if "Этаж / этажность" in mongo_data:
        try:
            floor, floors_total = [x.strip() for x in str(mongo_data["Этаж / этажность"]).split("/")]
            django_data["floor"] = int(floor)
            django_data.setdefault("building", {})["floors_total"] = int(floors_total)
        except (ValueError, AttributeError):
            pass

    # ----- Координаты -----
    if "Координаты" in mongo_data:
        try:
            coords = str(mongo_data["Координаты"]).split(",")
            if len(coords) == 2:
                lat, lon = [x.strip() for x in coords]
                loc = django_data.setdefault("building", {}).setdefault("location", {})
                loc["latitude"] = float(lat)
                loc["longitude"] = float(lon)
        except (ValueError, AttributeError):
            pass

    # ----- Адресные поля -----
    address_fields = {
        "building.location.town.region.name": ["Область", "Обл.", "Регион"],
        "building.location.town.name": ["Населенный пункт", "Город", "г."],
        "building.location.district": ["Район", "Р-н"],
        "building.location.street": ["Улица", "ул.", "Адрес"],
        "building.location.house_number": ["Дом", "Номер дома", "№ дома"]
    }

    # Если источник использует альтернативные названия, можно расширить:
    address_synonyms = {
        "separate_rooms": ["Раздельные комнаты", "Изолированные комнаты"]
    }

    # Пробуем заполнить адрес
    for path, mongo_fields in address_fields.items():
        for field in mongo_fields:
            if field in mongo_data:
                keys = path.split('.')
                current = django_data
                for key in keys[:-1]:
                    current = current.setdefault(key, {})
                current[keys[-1]] = str(mongo_data[field])
                break

    # Поддержка синонимов полей-значений
    for django_field, names in address_synonyms.items():
        if django_field not in django_data:
            for name in names:
                if name in mongo_data:
                    try:
                        django_data[django_field] = int(mongo_data[name])
                        break
                    except (ValueError, TypeError):
                        pass

    return django_data


if __name__ == "__main__":
    mongo_data = {'title': 'Снять 1-комнатную квартиру, г. Минск, ул. Неманская, 65', 'price': '1 369 р./мес.', 'Количество комнат': '1', 'Площадь общая': '37.6 м²', 'Площадь жилая': '17 м²', 'Площадь кухни': '9.2 м²', 'Этаж / этажность': '9 / 9', 'Ремонт': 'Евроремонт', 'Мебель': 'Есть', 'Парковка': 'Есть', 'Квартплата': '100%', 'Срок аренды': 'Длительный', 'Номер договора': '27/2а от 18.09.2025', 'Область': 'Минская область', 'Населенный пункт': 'г. Минск', 'Улица': 'Неманская ул.', 'Номер дома': '65', 'Район города': 'Фрунзенский район', 'Микрорайон': 'Каменная горка', 'Координаты': '53.9236, 27.4284', 'state': 'second', 'link': 'https://realt.by/rent-flat-for-long/object/3892738/'}

    django_data = transform_mongo_rent_to_django(mongo_data)
    print(json.dumps(django_data, ensure_ascii=False, indent=2))
