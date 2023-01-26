from bson.objectid import ObjectId
from cloud.minio_utils import *
from database.models import Chapter, Page
from flask import Response, request
from flask_restful import Resource
from mongoengine.errors import DoesNotExist, InvalidQueryError
from pdf_task import *
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
                pages = Page.objects(chapter=ObjectId(str(body["chapter_id"])))
                for page in pages:
                    if page.bounding_box_status == Status.READY:
                        if page.audio_status != Status.READY:
                            text_to_speech.si(str(page.id), page.get_audio_key()).apply_async()
                        continue
                    ( create_ocr_page.si(str(page.id), page.get_image_key(), page.get_pdf_key()) 
                        | bounding_box_preprocess.si(str(page.id), page.get_pdf_key()) 
                        | text_to_speech.si(str(page.id), page.get_audio_key())
                        | merge_chapter_pdf.si(str(page.chapter.id), json.dumps([ p.get_pdf_key() for p in page.chapter.pages]), page.chapter.get_pdf_key())
                        | concat_audio.si(str(page.chapter.id), json.dumps([ p.get_audio_key() for p in page.chapter.pages]), page.chapter.get_audio_key())
                    ).apply_async()
                    page.update(pdf_status=Status.PROCESSING,bounding_box_status=Status.PROCESSING, audio_status = Status.PROCESSING )
                    page.save()
                return f'successful OCR', 200
            # elif body["type"] == "single_page":
            #     #get
            #     page = Page.objects().get(id=ObjectId(str(body["id"])))
            #     chapter = page.chapter
            #     path = chapter.get_bucket_path()
            #     pdf_output = chapter.get_pdf_path()
            #     page_key = f"{path}/{page.page_number}.jpg"
            #     output = create_ocr_page(pdf_output, page_key)
            else:
                return 'error type body', 400 
        except InvalidQueryError:
            raise SchemaValidationError
        except Exception:
            raise InternalServerError       