import json

from celery import chain
from cloud.minio_utils import *
from database.models import Book, Chapter, EbookType, Sentence
from flask import Response, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource
from pdf_task import *


class BooksApi(Resource):
    def get(self):
        params = request.args.to_dict()
        if "text_search" in params:
            pages = Page.objects(sentences__text__contains=params['text_search'])
            list_book_id = [page.chapter.book_id for page in pages]
            result_search = {}
            for page in pages:
                chapter = page.chapter
                if chapter.id in result_search:
                    result_search[chapter.id]["pages"] += {"page": str(page.id), "page_number": page.page_number} 
                    continue
                result_search[chapter.id] = {"id": str(chapter.id), "chapter_name": chapter.chapter_number, "chapter_number": chapter.chapter_number, "pages":[{"page": str(page.id), "page_number": page.page_number} ]}
            books = json.loads(Book.objects(book_id__in=list_book_id).to_json())
            for book in books:
                results = []
                lst_chapter = set([page.chapter.id for page in pages  if page.chapter.book_id == book["book_id"]])
                for chapter_id in lst_chapter:
                    results.append(result_search[chapter_id])
                print(results)
                book['search_result'] = results
            return  books, 200
            # return Response(Sentence.objects.search_text(params['text_search']).order_by('$text_score'), status=200)
        else:
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
            if body["type_ebook"] == EbookType.PDF:
                book = Book(book_id = body['book_id'], type_ebook = EbookType.PDF) 
                book.save()
                book.create_chapters_and_pages(body["chapters_info"])
                for chapter in Chapter.objects(book_id=book.book_id):
                    for page in chapter.pages:
                        # pdf_app.split_page_pdf.apply_async((page.id, page.page_number, page.get_pdf_key(), page.get_image_key(),book.get_pdf_key()), link_error=[pdf_app.page_error.s("pdf_status", page.id), pdf_app.page_error.s("image_status", page.id), log_error.s()])
                        # (split_page_pdf.si(str(page.id), page.page_number, page.get_pdf_key(), page.get_image_key(), book.get_pdf_key()) | bounding_box_preprocess.si(str(page.id), page.get_pdf_key())).apply_async()
                        ( split_page_pdf.si(str(page.id), page.page_number, page.get_pdf_key(), page.get_image_key(), book.get_pdf_key())
                        | bounding_box_preprocess.si(str(page.id), page.get_pdf_key()) 
                        | text_to_speech.si(str(page.id), page.get_audio_key())
                        | merge_chapter_pdf.si(str(page.chapter.id), json.dumps([ p.get_pdf_key() for p in page.chapter.pages]), page.chapter.get_pdf_key())
                        | concat_audio.si(str(page.chapter.id), json.dumps([ p.get_audio_key() for p in page.chapter.pages]), page.chapter.get_audio_key())
                        ).apply_async()
                        page.update(image_status = Status.PROCESSING,pdf_status=Status.PROCESSING,bounding_box_status=Status.PROCESSING )
                        page.save()
                return {'id': str(book.id)}, 200
                # return "Cannot create split jobs", 500
            elif body["type_ebook"] == EbookType.OCR:
                book = Book(book_id = body['book_id'], type_ebook = EbookType.OCR) 
                book.save()
                return {'id': str(book.id)}, 200
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

