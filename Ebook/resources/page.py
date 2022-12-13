from bson.errors import InvalidId
from bson.objectid import ObjectId
from cloud.minio_utils import *
from database.models import Chapter, Page
from flask import Response, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource
from mongoengine.errors import (DoesNotExist, FieldDoesNotExist,
                                InvalidQueryError, NotUniqueError,
                                ValidationError)
from resources.base_errors import InvalidIdReq
from resources.page_errors import (DeletingPageError, InternalServerError,
                                   PageAlreadyExistsError, PageNotExistsError,
                                   SchemaValidationError, UpdatingPageError)


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
            chapter = Chapter.objects.get(id=chapter_id)
            page =  Page(**body, chapter=chapter)
            # path = chapter.get_bucket_path()
            # url = get_image_post_presigned_url(f"{path}/{page.page_number}.jpg")
            # if url is not None:
            #     page.image_url = url
            #     page.save()
            #     chapter.update(push__pages=page)
            #     chapter.save()
            # else:
            #     return {'message': "error! cannot upload to cloud"}, 503
            page.save()
            id = page.id
            return {'id': str(id), "url": page.image_url}, 200
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
            # user_id = get_jwt_identity()
            body = request.get_json()
            Page.objects.get(id=page_id).update(**body)
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
            page = Page.objects.get(id=id)
            page.delete()
            return 'delete successful', 200
        except DoesNotExist:
            raise DeletingPageError
        except Exception:
            raise InternalServerError

    def get(self, page_id):
        try:
            pages = Page.objects.get(id=page_id).to_json()
            return Response(pages, mimetype="application/json", status=200)
        except DoesNotExist:
            raise PageNotExistsError
        except Exception:
            raise InternalServerError
