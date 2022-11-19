from flask import Response, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource
from mongoengine.errors import (DoesNotExist, FieldDoesNotExist,
                                InvalidQueryError, NotUniqueError,
                                ValidationError)

from cloud.minio_ultis import *
from database.models import Chapter, Page
from resources.chapter_errors import (ChapterAlreadyExistsError,
                                      ChapterNotExistsError,
                                      DeletingChapterError,
                                      InternalServerError,
                                      SchemaValidationError,
                                      UpdatingChapterError)


class ChaptersApi(Resource):
    def get(self):
        status_find = request.args.get('status')
        query = Chapter.objects(status=status_find)
        Chapters = query.to_json()
        return Response(Chapters, mimetype="application/json", status=200)

    # @jwt_required
    def post(self):
        try:
            # user_id = get_jwt_identity()
            body = request.get_json()
            chapter = Chapter(**body)
            chapter.save()
            id = chapter.id
            return {'id': str(id)}, 200
        except (FieldDoesNotExist, ValidationError):
            raise SchemaValidationError
        except NotUniqueError:
            raise ChapterAlreadyExistsError
        except Exception as e:
            raise InternalServerError


class ChapterApi(Resource):
    @jwt_required
    def put(self, chapter_id):
        try:
            user_id = get_jwt_identity()
            Chapter = Chapter.objects.get(id=chapter_id, added_by=user_id)
            body = request.get_json()
            Chapter.objects.get(id=chapter_id).update(**body)
            return '', 200
        except InvalidQueryError:
            raise SchemaValidationError
        except DoesNotExist:
            raise UpdatingChapterError
        except Exception:
            raise InternalServerError       
    
    @jwt_required
    def delete(self, id):
        try:
            user_id = get_jwt_identity()
            Chapter = Chapter.objects.get(id=id, added_by=user_id)
            Chapter.delete()
            return '', 200
        except DoesNotExist:
            raise DeletingChapterError
        except Exception:
            raise InternalServerError

    def get(self, id):
        try:
            Chapters = Chapter.objects.get(id=id).to_json()
            return Response(Chapters, mimetype="application/json", status=200)
        except DoesNotExist:
            raise ChapterNotExistsError
        except Exception:
            raise InternalServerError
