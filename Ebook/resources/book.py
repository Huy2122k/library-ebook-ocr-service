import json

from celery import chain
from cloud.minio_utils import *
from database.models import Book, Chapter, EbookType
from flask import Response, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource
from pdf_task import *


class BooksApi(Resource):
    def get(self):
        query = Book.objects()
        res = query.to_json()
        return Response(res, mimetype="application/json", status=200)

    # @jwt_required
    def post(self):
        body = request.get_json()
        if body is None or "book_id" not in body or "type_ebook" not in body:
            return {'error': "missing book_id"}, 400
        print(body)
        try:
            # user_id = get_jwt_identity()
            if body["type_ebook"] == "pdf":
                book = Book(book_id = body['book_id'], type_ebook = EbookType.PDF) 
                book.save()
                book.create_chapters_and_pages(body["chapters_info"])
                print("heree")
                for chapter in Chapter.objects(book_id=book.book_id):
                    for page in chapter.pages:
                        # pdf_app.split_page_pdf.apply_async((page.id, page.page_number, page.get_pdf_key(), page.get_image_key(),book.get_pdf_key()), link_error=[pdf_app.page_error.s("pdf_status", page.id), pdf_app.page_error.s("image_status", page.id), log_error.s()])
                        (split_page_pdf.si(str(page.id), page.page_number, page.get_pdf_key(), page.get_image_key(), book.get_pdf_key()) | bounding_box_preprocess.si(str(page.id), page.get_image_key())).apply_async()
                id = book.id
                return {'id': str(id)}, 200
                # return "Cannot create split jobs", 500
            else:
                return {'error': "bad type"}, 400
        except Exception as e:
            print(e)
            book = Book.objects(book_id=body["book_id"]).first()
            if book:
                book.delete_book()
            return {'error': str(e)}, 500

class BookApi(Resource):
    def get(self, book_id):
        query = Book.objects(book_id=book_id).first()
        res = query
        if query:
            res = json.loads(query.to_json())
            res["chapters"] = []
            chapters = Chapter.objects(book_id=book_id)
            for chapter in chapters:
                chapter_dict = json.loads(chapter.to_json())
                chapter_dict["status"] = chapter.status
                res["chapters"] += [chapter_dict]  
        return res, 200

