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

# pdf_process_app = Celery('pdf_process',
#              broker='amqp://admin:mypass@localhost:5672',
#              backend='mongodb://localhost:27017/mydb')

app = Flask(__name__)
app.debug = True
cors = CORS(app)
app.config.from_envvar('ENV_FILE_LOCATION')
mail = Mail(app)

# imports requiring app and mail
from resources.routes import initialize_routes

api = Api(app, errors=errors)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

initialize_db(app)
initialize_routes(api)
