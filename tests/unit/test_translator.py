import pytest
import math

from app.translator import transform_mongo_apartments_to_django


def test_defaults_are_applied_when_no_fields():
    out = transform_mongo_apartments_to_django({})
    assert out["title"] == "Без названия"
    assert out["price"] == 0.0
    assert out["room_count"] == 1
    assert out["description"] == "Нет описания"
    assert out["floor"] == 1
    loc = out["building"]["location"]
    assert loc["street"] == "Не указана"
    assert loc["house_number"] == "0"
    assert loc["town"]["name"] == "Не указан"
    assert loc["town"]["region"]["name"] == "Не указан"


def test_direct_mapping_fields():
    mongo = {
        "title": "Тестовая квартира",
        "link": "http://example.com/flat/1",
        "description": "Описание",
        "Номер договора": "ABC123",
        "Ремонт": "Евроремонт",
    }
    out = transform_mongo_apartments_to_django(mongo)
    assert out["title"] == "Тестовая квартира"
    assert out["link"] == "http://example.com/flat/1"
    assert out["description"] == "Описание"
    assert out["contract_number"] == "ABC123"
    assert out["renovation"] == "Евроремонт"


def test_numeric_mappings_and_parsing():
    mongo = {
        "price": "277 770 р.",
        "Площадь общая": "78 м²",
        "Площадь жилая": "74 м²",
        "Площадь кухни": "12,5 м²",
        "Количество комнат": "3",
        "Высота потолков": "2.7 м",
        "Год постройки": "2019",
    }
    out = transform_mongo_apartments_to_django(mongo)
    assert math.isclose(out["price"], 277770.0)
    assert math.isclose(out["total_area"], 78.0)
    assert math.isclose(out["living_area"], 74.0)
    assert math.isclose(out["kitchen_area"], 12.5)
    assert out["room_count"] == 3
    assert math.isclose(out["ceiling_height"], 2.7)
    assert out["building"]["construction_year"] == 2019


@pytest.mark.parametrize("val,expected", [
    ("Лоджия", "Loggia"),
    ("Балкон", "Classic"),
    ("Французский балкон", "French"),
    ("Угловой балкон", "Extended"),
    ("Нет", "No"),
    ("Отсутствует", "No"),
    ("Другое", "No"),
])
def test_choice_mapping_balcony(val, expected):
    mongo = {"Балкон": val}
    out = transform_mongo_apartments_to_django(mongo)
    assert out["balcony"] == expected


def test_choice_mapping_other_fields():
    mongo = {
        "Условия продажи": "Альтернатива",
        "Состояние": "Хорошее",
        "Собственность": "Государственная",
        "Тип дома": "Кирпичный",
    }
    out = transform_mongo_apartments_to_django(mongo)
    assert out["sale_conditions"] == "Alternative"
    assert out["condition"] == "Good"
    assert out["ownership_type"] == "State"
    assert out["building"]["wall_material"] == "Brick"


def test_floor_and_floors_total():
    mongo = {"Этаж / этажность": "6 / 7"}
    out = transform_mongo_apartments_to_django(mongo)
    assert out["floor"] == 6
    assert out["building"]["floors_total"] == 7


def test_coordinates():
    mongo = {"Координаты": "53.6673, 23.8516"}
    out = transform_mongo_apartments_to_django(mongo)
    loc = out["building"]["location"]
    assert math.isclose(loc["latitude"], 53.6673)
    assert math.isclose(loc["longitude"], 23.8516)


def test_address_fields_mapping():
    mongo = {
        "Область": "Гродненская область",
        "Населенный пункт": "Гродно",
        "Улица": "Лидская ул.",
        "Номер дома": "33",
        "Район": "Гродненский район",
    }
    out = transform_mongo_apartments_to_django(mongo)
    loc = out["building"]["location"]
    assert loc["town"]["region"]["name"] == "Гродненская область"
    assert loc["town"]["name"] == "Гродно"
    assert loc["street"] == "Лидская ул."
    assert loc["house_number"] == "33"
    assert loc["district"] == "Гродненский район"


def test_invalid_numeric_values_are_ignored():
    mongo = {
        "Площадь общая": "не число",
        "Количество комнат": None,
    }
    out = transform_mongo_apartments_to_django(mongo)
    assert out["total_area"] == 0.0
    assert out["room_count"] == 1


def test_invalid_coordinates_are_ignored():
    mongo = {"Координаты": "abc,xyz"}
    out = transform_mongo_apartments_to_django(mongo)
    loc = out["building"]["location"]
    assert loc["latitude"] is None
    assert loc["longitude"] is None
