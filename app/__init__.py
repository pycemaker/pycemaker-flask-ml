from .routes import create_routes
import os
from flask import Flask, app
from flask_restful import Api
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv('.env')


def get_flask_app(config: dict = None) -> app.Flask:
    flask_app = Flask(__name__)
    api = Api(app=flask_app)
    create_routes(api=api)
    CORS(flask_app)

    return flask_app