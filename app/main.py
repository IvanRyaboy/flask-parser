from flask import Flask, request, jsonify
from flask_restful import Api, Resource, reqparse
from database import get_apartments_db
import jwt
from jwt import PyJWKClient, InvalidTokenError
import os
from dotenv import load_dotenv

load_dotenv()
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
JWKS_URL = os.getenv("LWKS_URL")


app = Flask(__name__)
api = Api(app)
AUDIENCE = os.getenv("AUDIENCE")
ISSUER = os.getenv("ISSUER")


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
        db = get_apartments_db()
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


api.add_resource(Apartment, "/apartments/<id>")


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
