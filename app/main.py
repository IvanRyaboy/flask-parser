from services import put_apartment_info_from_realt_to_mongo
import requests
from flask import Flask, request, jsonify
from flask_restful import Api, Resource, reqparse
from database import get_db
import jwt
from jwt import PyJWKClient, InvalidTokenError
import os
from dotenv import load_dotenv
from celery import chain
from tasks import parse_apartment_list, parse_apartment_details, send_webhook_to_django

# load_dotenv()
# AZURE_TENANT_ID =
# AZURE_CLIENT_ID =
# JWKS_URL =
#
#
# app = Flask(__name__)
# api = Api(app)
# AUDIENCE =
# ISSUER =


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
    db = get_db()
    coll = db.apartments

    def get(self, id='0'):
        auth_header = request.headers.get("Authorization", "")
        token = None

        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:]

        if not token:
            return jsonify({"error": "Token missing"}), 401

        payload = validate_token(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 402

        apartment = self.coll.find_one(filter={'_id': id})

        if apartment:
            return apartment
        else:
            return jsonify({"error": "Apartment not found"}), 404


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
    task = send_webhook_to_django.delay()

    return jsonify({
        'message': 'Задача отправки вебхука запущена',
        'task_id': task.id,
        'status_check_url': f'/check_task_status/{task.id}'
    })


@app.route('/check_data', methods=['GET'])
def check_data():
    db = get_db()
    collection = db.apartments

    apartment = collection.find_one()
    if collection.count_documents({}) > 0:
        return apartment
    else:
        return jsonify({"data_exists": False})


api.add_resource(Apartment, "/apartments/<id>")


app.run(host='0.0.0.0', port=5000)
