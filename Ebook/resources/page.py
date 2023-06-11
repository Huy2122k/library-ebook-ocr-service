import json

import unidecode
from bson.errors import InvalidId
from bson.objectid import ObjectId
from cloud.minio_utils import *
from database.models import Chapter, Page, Sentence, Status
from flask import Response, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource
from mongoengine.errors import (DoesNotExist, FieldDoesNotExist,
                                InvalidQueryError, NotUniqueError,
                                ValidationError)
from pdf_task import *
from resources.base_errors import InvalidIdReq
from resources.page_errors import (DeletingPageError, InternalServerError,
                                   PageAlreadyExistsError, PageNotExistsError,
                                   SchemaValidationError, UpdatingPageError)


def remove_accent(text):
    return unidecode.unidecode(text)

class PagesApi(Resource):
    def get(self):
        try:
            params = dict(request.args)
            if "chapter_id" in params:
                params["chapter"] = ObjectId(str(params.pop("chapter_id", None)))
            query = Page.objects(**params).to_json()
            pages = Page.objects().to_json()
            return Response(query, mimetype="application/json", status=200)
        except InvalidId:
            raise InvalidIdReq

    # @jwt_required
    def post(self):
        try:
            # user_id = get_jwt_identity()
            body = request.get_json()
            chapter_id = body.pop("chapter_id")
            page_type = body.pop("page_type")
            if page_type == "page_ocr":
                chapter = Chapter.objects.get(id=chapter_id)
                page =  Page(**body, chapter=chapter)
                page.save()
                chapter.update(push__pages=page)
                chapter.save()
                url = generate_presigned_url(object_key=page.get_image_key(), method="PUT")
                return {'id': str(page.id), "presigned_url": url}, 200
            else:
                return {'msg':"unsupported type page"}, 400
        except (FieldDoesNotExist, ValidationError):
            raise SchemaValidationError
        except NotUniqueError:
            raise PageAlreadyExistsError
        except Exception as e:
            raise InternalServerError


class PageApi(Resource):
    # @jwt_required
    def put(self, page_id):
        try:
            body = request.get_json()
            page =  Page.objects.get(id=page_id)
            # change sentences
            if "sentences" in body:
                # replace all
                Sentence.objects(page = page).delete()
                #bulk create
                new_sentences= [Sentence(**se, text_search=remove_accent(se["text"]), page = page) for se in body["sentences"]]
                new_sentence_ids = Sentence.objects.insert(new_sentences, load_bulk=False)
                page.update(
                    sentences = new_sentence_ids
                )
                del body["sentences"]
                page.update(
                    **body
                )
                page.save()
                return {"page_id": page_id,"msg":"create sentences successful"}, 200
            #else update
            page.update(**body)
            return 'successful', 200
        except InvalidQueryError:
            raise SchemaValidationError
        except DoesNotExist:
            raise UpdatingPageError
        except Exception:
            raise InternalServerError       
    
    # @jwt_required
    def delete(self, page_id):
        try:
            # user_id = get_jwt_identity()
            page = Page.objects.get(id=page_id)
            page.delete()
            return 'delete successful', 200
        except DoesNotExist:
            raise DeletingPageError
        except Exception:
            raise InternalServerError

    def get(self, page_id):
        try:
            page = Page.objects.get(id=page_id)
            page_with_presign = self.append_image_presign_url(page)
            return page_with_presign, 200
        except DoesNotExist:
            raise PageNotExistsError
        except Exception:
            raise InternalServerError
    def append_image_presign_url(self,page):
        page_dict = json.loads(page.to_json())
        page_dict["presigned_img"] = generate_presigned_url(page.get_image_key(),"GET", "image/*") 
        page_dict["presigned_pdf"] =  generate_presigned_url(page.get_pdf_key(),"GET", "application/pdf") 
        page_dict["presigned_audio"] =  generate_presigned_url(page.get_audio_key(),"GET", "audio/mpeg")
        page_dict['sentences'] = json.loads(Sentence.objects.filter(page=page).to_json())
        return page_dict
