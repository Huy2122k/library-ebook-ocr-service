import os
import sys

os.environ['ENV_FILE_LOCATION'] = ".env"

from celery import Celery
from database.db import initialize_db
from flask import Flask
from flask_bcrypt import Bcrypt
from flask_cors import CORS, cross_origin
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_restful import Api
from resources.errors import errors
from resources.routes import AppRoutes

app = Flask(__name__)
app.debug = True
cors = CORS(app)
app.config.from_envvar('ENV_FILE_LOCATION')
mail = Mail(app)

api = Api(app, errors=errors)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
routes = AppRoutes(api)
routes.init_routes()
initialize_db(app)
