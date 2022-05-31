from .routes import create_routes
import os
from flask import Flask, app
from flask_restful import Api
from flask_mongoengine import MongoEngine
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv('.env')


def get_flask_app(config: dict = None) -> app.Flask:

    flask_app = Flask(__name__)

    flask_app.config['MONGODB_HOST'] = os.environ.get("MONGO_DB_URL")

    flask_app.config['JWT_SECRET_KEY'] = os.environ.get("JWT_SECRET_KEY")

    api = Api(app=flask_app)
    create_routes(api=api)

    db = MongoEngine(app=flask_app)

    jwt = JWTManager(app=flask_app)

    CORS(flask_app)

    return flask_app
