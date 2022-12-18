from cloud.minio_utils import *
from database.models import Book, Chapter, Page
from flask import Response, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource
from mongoengine.errors import (DoesNotExist, FieldDoesNotExist,
                                InvalidQueryError, NotUniqueError,
                                ValidationError)
from resources.chapter_errors import (ChapterAlreadyExistsError,
                                      ChapterNotExistsError,
                                      DeletingChapterError,
                                      InternalServerError,
                                      SchemaValidationError,
                                      UpdatingChapterError)


class ChaptersApi(Resource):
    def get(self):
        params = request.args.to_dict()
        if params:
            query = Chapter.objects(**params).get_chapters_detail()
            # chapters = query.to_json()
            return query, 200
        return [], 200
    # @jwt_required
    def post(self):
        try:
            # user_id = get_jwt_identity()
            body = request.get_json()
            chapter = Chapter(**body)
            chapter.save()
            return Response(chapter.to_json(), mimetype="application/json", status=200)
        except (FieldDoesNotExist, ValidationError):
            raise SchemaValidationError
        except NotUniqueError:
            raise ChapterAlreadyExistsError
        except Exception as e:
            raise InternalServerError


class ChapterApi(Resource):
    def get(self, chapter_id):
        try:
            Chapters = Chapter.objects.get(id=chapter_id).to_json()
            return Response(Chapters, mimetype="application/json", status=200)
        except DoesNotExist:
            raise ChapterNotExistsError
        except Exception:
            raise InternalServerError
    # @jwt_required
    def put(self, chapter_id):
        try:
            body = request.get_json()
            Chapter.objects.get(id=chapter_id).update(**body)
            return 'update successful', 200
        except InvalidQueryError:
            raise SchemaValidationError
        except DoesNotExist:
            raise UpdatingChapterError
        except Exception:
            raise InternalServerError       
    
    # @jwt_required
    def delete(self, chapter_id):
        try:
            user_id = get_jwt_identity()
            Chapter = Chapter.objects.get(id=chapter_id)
            Chapter.delete()
            return '', 200
        except DoesNotExist:
            raise DeletingChapterError
        except Exception:
            raise InternalServerError


