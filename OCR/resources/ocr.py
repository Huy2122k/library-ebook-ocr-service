from bson.objectid import ObjectId
from flask import Response, request
from flask_restful import Resource
from mongoengine.errors import DoesNotExist, InvalidQueryError

from utils.ocr_utils import *
from resources.page_errors import InternalServerError, SchemaValidationError
from cloud.minio_utils import *


# required_body = {
#     'img_object_key': ...,
#     'pdf_object_key': ...,
# }

class OcrApi(Resource):
    # @jwt_required
    def post(self):
        try:
            # user_id = get_jwt_identity()
            body = request.get_json()
            output = create_ocr_page(body['img_object_key'], body['pdf_object_key'])
            return f'successful {output}', 200
        except InvalidQueryError:
            raise SchemaValidationError
        except Exception:
            raise InternalServerError       