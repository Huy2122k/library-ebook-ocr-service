from enum import Enum

from bson.objectid import ObjectId
from flask_bcrypt import check_password_hash, generate_password_hash

from .db import db

BOOK_STATUS = {'PROCESSING', 'READY'}
class Status(str, Enum):
    NEW = "new"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"

class EbookType(str, Enum):
    PDF="pdf",
    OCR="ocr",
    OTHER="other"

class Sentence(db.EmbeddedDocument):
    page = db.ReferenceField('Page', required=True)
    index = db.IntField(required=True)
    text = db.StringField()
    bounding_box = db.ListField(default=[])
    audio_timestamp = db.FloatField(default=None)
    meta = {
        'indexes': [
            {
                'fields': "text", 
            }
        ]
    }
class Page(db.Document):
    chapter = db.ReferenceField("Chapter", required=True)
    page_number = db.IntField(required=True)
    pdf_status = db.EnumField(Status, default=Status.NEW, validators=None )
    image_status = db.EnumField(Status, default=Status.NEW, validators=None)
    ocr_status = db.EnumField(Status, default=Status.NEW, validators=None)
    audio_status = db.EnumField(Status, default=Status.NEW, validators=None)
    audio_length = db.FloatField()
    sentences = db.ListField(db.EmbeddedDocumentField('Sentence'), default=[])
    meta = {
        'indexes': [
            {
                'fields': ['chapter', 'page_number'],
                'unique': True  
            }
        ]
    }
    def get_image_key(self):
        return f"{self.chapter.book_id}/chapter_{self.chapter.chapter_number}/page_img/page_{self.page_number}_{self.id}.jpg"
    def get_pdf_key(self):
        return f"{self.chapter.book_id}/chapter_{self.chapter.chapter_number}/page_pdf/page_{self.page_number}_{self.id}.pdf"
    def get_audio_key(self):
        return f"{self.chapter.book_id}/chapter_{self.chapter.chapter_number}/page_audio/page_{self.page_number}_{self.id}.mp3"
class Chapter(db.Document):
    book_id = db.StringField(required=True)
    chapter_name = db.StringField(required=True)
    pages = db.ListField(db.ReferenceField('Page', reverse_delete_rule=db.PULL), default=[])
    chapter_number = db.IntField(required=True)
    chapter_from = db.IntField(default = 0)
    chapter_to = db.IntField(default = 0)
    # pdf_status = db.EnumField(Status, default=Status.NEW)
    meta = {
        'indexes': [
            {
                'fields': ['book_id', 'chapter_number'],
                'unique': True  
            },
            {
                'fields': ['book_id'],
                'unique': False  
            },
        ]
    }
    def get_pdf_key(self):
        return f"{self.book_id}/chapter_{self.chapter_number}/{self.id}.pdf" 
    def check_status(self, attribute):
        if any(page[attribute] == Status.ERROR for page in self.pages):
            return "error"
        elif all(page[attribute] == Status.READY for page in self.pages):
            return "ready"
        elif any(page[attribute] == Status.PROCESSING for page in self.pages):
            return "processing"
        else:
            return "new"
    @property
    def creation_stamp(self):
        return self.id.generation_time
    @property
    def status(self):
        return {
            "pdf_status" : self.check_status("pdf_status"),
            "image_status" : self.check_status("image_status"),
            "ocr_status"  : self.check_status("ocr_status"),
            "audio_status" : self.check_status("audio_status")
        }
        
class Book(db.Document):
    book_id = db.StringField(required=True, unique=True)
    type_ebook = db.EnumField(EbookType, default=EbookType.PDF)
    meta = {
        'indexes': [
            {
                'fields': ['book_id'],
                'unique': True  
            },
        ]
    }
    def create_chapters_and_pages(self, chapters_info):
        #create chapter
        for index, chapter_info in enumerate(chapters_info):
            chapter = Chapter(book_id=self.book_id,chapter_name=chapter_info["chapter_name"], chapter_number=index, chapter_from=chapter_info["chapter_from"], chapter_to = chapter_info["chapter_to"])
            chapter.save()
            #create pages
            for number in range(int(chapter_info["chapter_from"]), int(chapter_info["chapter_to"] + 1)):
                page = Page(chapter=chapter, page_number = number, ocr_status = Status.READY)
                page.save()
                chapter.update(push__pages=page)
            chapter.save()
        # print()
    def delete_book(self):
        chapters = Chapter.objects(book_id=self.book_id)
        for chapter in chapters:
            chapter.delete()
    def get_pdf_key(self):
        return f"{self.book_id}/{self.book_id}.pdf"

Chapter.register_delete_rule(Page, 'chapter', db.CASCADE)
