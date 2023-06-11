import json

from bson.objectid import ObjectId
from cloud.minio_utils import *
from database.models import Book, Chapter, Page
from flask import Response, jsonify, make_response, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource
from mongoengine.connection import get_connection
from mongoengine.errors import (DoesNotExist, FieldDoesNotExist,
                                InvalidQueryError, NotUniqueError,
                                ValidationError)
from pdf_task import *
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
            if "book_id__in" in params:
                print(type(params["book_id__in"]))
                query = Chapter.objects.filter(book_id__in=json.loads(params["book_id__in"])).get_chapters_detail()
                return query, 200
            query = Chapter.objects.filter(**params).get_chapters_detail()
            # chapters = query.to_json()
            return query, 200
        return Chapter.objects.all().to_json(), 200
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
            chapter = Chapter.objects.get(id=chapter_id)
            chapter_dict = json.loads(chapter.to_json())
            chapter_dict["status"] = chapter.status
            return chapter_dict, 200
        except DoesNotExist:
            raise ChapterNotExistsError
        except Exception:
            raise InternalServerError
    # @jwt_required
    def put(self, chapter_id):
        try:
            body = request.get_json()
            if "pages" in body:
                chapter = Chapter.objects.get(id=chapter_id)
                chapter.pages=[ObjectId(page_id) for page_id in body.pop("pages")]
                if body:
                    chapter.update(**body)
                chapter.save()
                (   merge_chapter_pdf.si(str(chapter.id), json.dumps([ p.get_pdf_key() for p in chapter.pages]), chapter.get_pdf_key())
                    | concat_audio.si(str(chapter.id), json.dumps([ p.get_audio_key() for p in chapter.pages]), chapter.get_audio_key())
                ).apply_async()
                return 'update successful', 200
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



# route api/chapter_meta/<chapter_id>
class ChapterGetAllApi(Resource):
    # Lấy toàn bộ thông tin chapter (chapter, pages, sentences)
    # Cấu trúc 
    # Lưu ý: Trong bounding box, các thông số lấy theo % của page (hiện tại đang set mặc định A4: width=595, height=842)
    # {
    #     chapter: <chapter_info>,
    #     sentences: [
    #         {
    #             page_index: ,
    #             sentence_id: ,
    #             text: ,
    #             start_time: ,
    #             bounding_boxes: [
    #                 {
    #                     x: ,
    #                     y: ,
    #                     width: ,
    #                     height: ,
    #                     page_index: 
    #                 }
    #             ]
    #         }
    #     ]
    # }
    def get(self, chapter_id):
        mongo = get_connection()
        with mongo.start_session() as session:
            with session.start_transaction():
                try:
                    chapter = Chapter.objects.get(id=chapter_id)
                    num_chapter = len(Chapter.objects(book_id=chapter.book_id))
                    pages = chapter.pages
                    sentence_list = []
                    time_between_sentence = 0.0 # Thời gian giữa 2 câu
                    total_time = 0
                    for i in pages:
                        sentences = i.sentences
                        for j in sentences:
                            if "audio_timestamp" not in j:
                                continue
                            total_time += j['audio_timestamp']
                            sentence_item = {}
                            sentence_item['pageIndex'] = pages.index(i)
                            sentence_item['sentenceId'] = f"{i['id']}-{j['index']}"
                            sentence_item['endTime'] = total_time
                            sentence_item['duration'] = j['audio_timestamp']
                            total_time += time_between_sentence
                            bounding_box_list = []
                            for k in j['bounding_box']:
                                bounding_box_list.append({
                                    'pageIndex': pages.index(i),
                                    'left': (k['x']/595)*100,
                                    'top': (k['y']/842)*100,
                                    'width': (k['width']/595)*100,
                                    'height': (k['height']/842)*100,
                                    "text": j["text"]
                                })
                            sentence_item['highlightAreas'] = bounding_box_list
                            sentence_list.append(sentence_item)
                    return make_response(jsonify({'urls':chapter.get_public_urls(),'chapter': chapter, 'numChapter': num_chapter,'sentences': sentence_list}), 200)
                except (FieldDoesNotExist, ValidationError):
                    session.abort_transaction()
                    raise SchemaValidationError
                except NotUniqueError:
                    session.abort_transaction()
                    raise ChapterAlreadyExistsError
                except Exception as e:
                    session.abort_transaction()
                    raise InternalServerError
