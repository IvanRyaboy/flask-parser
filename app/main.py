from flask import Flask, request, jsonify
from flask_restful import Api, Resource, reqparse
from database import get_client
import jwt
from jwt import PyJWKClient, InvalidTokenError
import os
from dotenv import load_dotenv
from tasks import *
import logging

logger = logging.getLogger(__name__)


load_dotenv()
AZURE_TENANT_ID = os.getenv('AZURE_TENANT_ID')
AZURE_CLIENT_ID = os.getenv('AZURE_CLIENT_ID')
JWKS_URL = f'https://login.microsoftonline.com/{AZURE_TENANT_ID}/discovery/v2.0/keys'


app = Flask(__name__)
api = Api(app)
AUDIENCE = os.getenv('AZURE_CLIENT_ID')
ISSUER = f'https://login.microsoftonline.com/{AZURE_TENANT_ID}/v2.0'


def validate_token(token):
    try:
        jwks_client = PyJWKClient(JWKS_URL)
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=AUDIENCE,
            issuer=ISSUER,
        )
        return payload
    except InvalidTokenError as e:
        print(f"Token validation error: {str(e)}")
        return None


class Apartment(Resource):

    def get(self, id='0'):
        client = get_client()
        db = client.apartments
        coll = db.apartments

        auth_header = request.headers.get("Authorization", "")
        token = None

        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:]

        if not token:
            return {"error": "Token missing"}, 401

        payload = validate_token(token)
        if not payload:
            return {"error": "Invalid or expired token"}, 402

        apartment = coll.find_one(filter={'_id': id})

        if apartment:
            return apartment
        else:
            return {"error": "Apartment not found"}, 404


class Rent(Resource):
    def get(self, id='0'):
        client = get_client()
        db = client.rental
        coll = db.rental

        auth_header = request.headers.get("Authorization", "")
        token = None

        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:]

        if not token:
            return {"error": "Token missing"}, 401

        payload = validate_token(token)
        if not payload:
            return {"error": "Invalid or expired token"}, 402

        rent = coll.find_one(filter={'_id': id})

        if rent:
            return rent
        else:
            return {"error": "Rent not found"}, 404


@app.route('/test_parse_list')
def test_parse_list():
    """Запуск задачи парсинга списка квартир"""
    task = parse_apartment_list.delay()
    return jsonify({
        'message': 'Парсинг списка квартир запущен',
        'task_id': task.id,
        'status_url': f'/check_task_status/{task.id}'
    })


@app.route('/test_parse_details')
def test_parse_details():
    """Запуск задачи парсинга деталей квартир"""
    task = parse_apartment_details.delay()
    return jsonify({
        'message': 'Парсинг деталей квартир запущен',
        'task_id': task.id,
        'status_url': f'/check_task_status/{task.id}'
    })


@app.route('/test_webhook')
def test_webhook():
    task = send_apartments_webhook_to_django.delay()

    return jsonify({
        'message': 'Задача отправки вебхука запущена',
        'task_id': task.id,
        'status_check_url': f'/check_task_status/{task.id}'
    })


@app.route('/test_rent_list')
def test_rent_list():
    task = parse_rent_list.delay()
    return jsonify({
        'message': 'Start',
        'task_id': task.id,
        'status_url': f'/check_task_status/{task.id}'
    })


@app.route('/test_rent_details')
def test_rent_details():
    """Запуск задачи парсинга деталей квартир"""
    task = parse_rent_details.delay()
    return jsonify({
        'message': 'Парсинг деталей квартир запущен',
        'task_id': task.id,
        'status_url': f'/check_task_status/{task.id}'
    })


@app.route('/rent_webhook')
def rent_webhook():
    task = send_rent_webhook_to_django.delay()

    return jsonify({
        'message': 'Задача отправки вебхука запущена',
        'task_id': task.id,
        'status_check_url': f'/check_task_status/{task.id}'
    })


api.add_resource(Apartment, "/apartments/<id>")
api.add_resource(Rent, "/rent/<id>")


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
