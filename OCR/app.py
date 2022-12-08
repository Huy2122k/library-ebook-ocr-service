import os
import sys

os.environ['ENV_FILE_LOCATION'] = ".env"

from flask import Flask
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_restful import Api

from resources.errors import errors

app = Flask(__name__)

# imports requiring app and mail
from resources.routes import initialize_routes

api = Api(app, errors=errors)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

initialize_routes(api)
