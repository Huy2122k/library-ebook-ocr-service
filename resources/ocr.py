from bson.objectid import ObjectId
from flask import Response, request
from flask_restful import Resource
from mongoengine.errors import DoesNotExist, InvalidQueryError

from cloud.minio_utils import *
from database.models import Chapter, Page
from ocr.ocr_utils import *
from resources.page_errors import InternalServerError, SchemaValidationError

# required_body = {
#     'type': "chapter" | "single_page",
#     'id': "6378b1fbc462477c40e1948f"
# }


class OcrApi(Resource):
    # @jwt_required
    def post(self):
        try:
            # user_id = get_jwt_identity()
            body = request.get_json()
            if body["type"] == "chapter":
                #get
                pages = Page.objects(chapter=ObjectId(str(body["id"])))
            elif body["type"] == "single_page":
                #get
                page = Page.objects().get(id=ObjectId(str(body["id"])))
                chapter = page.chapter
                path = chapter.get_bucket_path()
                pdf_output = chapter.get_pdf_path()
                page_key = f"{path}/{page.page_number}.jpg"
                output = create_ocr_page(pdf_output, page_key)
            else:
                return 'error type body', 400 
            return f'successful {output}', 200
        except InvalidQueryError:
            raise SchemaValidationError
        except Exception:
            raise InternalServerError       