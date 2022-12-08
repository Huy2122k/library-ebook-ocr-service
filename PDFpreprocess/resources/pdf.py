from bson.objectid import ObjectId
from flask import Response, request
from flask_restful import Resource
from mongoengine.errors import DoesNotExist, InvalidQueryError

from utils.pdf_utils import *
from resources.page_errors import InternalServerError, SchemaValidationError
from cloud.minio_utils import *


# required_body = {
#     'page-id': "6378b1fbc462477c40e1948f"
#     'pdf_object_key': ...
# }

class BBCreateApi(Resource):
    # @jwt_required
    def post(self):
        try:
            # user_id = get_jwt_identity()
            body = request.get_json()
            output = bounding_box_preprocess(body['pdf_object_key'])
            return f'{output}', 200
        except InvalidQueryError:
            raise SchemaValidationError
        except Exception:
            raise InternalServerError   

# required_body = {
#     'img_object_key': ...,
#     'pdf_object_key': ...
# }

class PdfConverterApi(Resource):
    # @jwt_required
    def post(self):
        try:
            # user_id = get_jwt_identity()
            body = request.get_json()
            output = convert_pdf_to_image(body['pdf_object_key'], body['img_object_key'])
            return f'{output}', 200
        except InvalidQueryError:
            raise SchemaValidationError
        except Exception:
            raise InternalServerError  

# required_body = {
#   'book_pdf_object_key': ...,
#   'from': ...,
#   'to': ...,
#   'chapter_pdf_object_key': ...
# }
class SplitBookApi(Resource):
    # @jwt_required
    def post(self):
        try:
            # user_id = get_jwt_identity()
            body = request.get_json()
            output = split_book(body['book_pdf_object_key'], int(body['from']), int(body['to']), body['chapter_pdf_object_key'])
            return f'{output}', 200
        except InvalidQueryError:
            raise SchemaValidationError
        except Exception:
            raise InternalServerError  