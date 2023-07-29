import json

from bson.objectid import ObjectId
from database.models import Chapter, Page, Status
from flask import Response, request
from flask_restful import Resource
from mongoengine.errors import DoesNotExist, InvalidQueryError
from pdf_task import pdf_app
from resources.page_errors import InternalServerError, SchemaValidationError


class TaskApi(Resource):
    # @jwt_required
    
    def __init__(self, *args):
        super(TaskApi, self).__init__(*args)
        self.pdf_app = pdf_app
        self.init_task()
        print("==================INIT================")

    def init_task(self):    
        for task in ("bounding_box_preprocess", "concat_audio", "create_ocr_page",
                    "merge_chapter_pdf", "text_to_speech"):
            setattr(self, task, self.pdf_app.tasks.get(f"pdf_task.{task}"))

    '''
        API POST
        required_body = {
            'type': "chapter" | "single_page",
            'id': "6378b1fbc462477c40e1948f"
        }
    '''
    def post(self):
        try:
            # user_id = get_jwt_identity()
            print(self.pdf_app.tasks)
            body = request.get_json()
            if body["type"] == "chapter":
                self.run_ebook_create_for_chapter(ObjectId(str(body["chapter_id"])))
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

    def run_ebook_create_for_chapter(self, chapter_id):
        pages = Page.objects(chapter=chapter_id)
        for page in pages:
            if page.bounding_box_status == Status.READY:
                if page.audio_status != Status.READY:
                    self.run_ebook_create_for_page(page, step="audio")
                continue
            self.run_ebook_create_for_page(page, step="all")
            page.update(pdf_status=Status.PROCESSING,bounding_box_status=Status.PROCESSING, audio_status = Status.PROCESSING )
            page.save()

    def run_ebook_create_for_page(self, page, step="all"):  
        if step == "audio":
            (self.text_to_speech.si(str(page.id), page.get_audio_key())
                | self.merge_chapter_pdf.si(str(page.chapter.id), json.dumps([ p.get_pdf_key() for p in page.chapter.pages]), page.chapter.get_pdf_key())
                | self.concat_audio.si(str(page.chapter.id), json.dumps([ p.get_audio_key() for p in page.chapter.pages]), page.chapter.get_audio_key())
            ).apply_async()
        else:
            ( self.create_ocr_page.si(str(page.id), page.get_image_key(), page.get_pdf_key()) 
                    | self.bounding_box_preprocess.si(str(page.id), page.get_pdf_key()) 
                    | self.text_to_speech.si(str(page.id), page.get_audio_key())
                    | self.merge_chapter_pdf.si(str(page.chapter.id), json.dumps([ p.get_pdf_key() for p in page.chapter.pages]), page.chapter.get_pdf_key())
                    | self.concat_audio.si(str(page.chapter.id), json.dumps([ p.get_audio_key() for p in page.chapter.pages]), page.chapter.get_audio_key())
                ).apply_async()
            
