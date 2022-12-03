from enum import Enum

from bson.objectid import ObjectId
from flask_bcrypt import check_password_hash, generate_password_hash

from .db import db

BOOK_STATUS = {'PROCESSING', 'READY'}
class Status(Enum):
    NEW = "new"
    PROCESSING = 'processing'
    READY = 'ready'

class Page(db.Document):
    image_url = db.URLField(required=True, unique=True)
    chapter = db.ReferenceField("Chapter", required=True)
    page_number = db.IntField(required=True)
    meta = {
        'indexes': [
            {
                'fields': ['chapter', 'page_number'],
                'unique': True  
            }
        ]
    }
class Chapter(db.Document):
    book_id = db.StringField(required=True, unique=True)
    chapter_name = db.StringField(required=True)
    pdf_url = db.URLField(required=False)
    pages = db.ListField(db.ReferenceField('Page', reverse_delete_rule=db.PULL), default=[])
    status = db.EnumField(Status, default=Status.NEW)
    meta = {
        'indexes': [
            {
                'fields': ['book_id'],
                'unique': True  
            },
            {
                'fields': ['book_id', 'pdf_url'],
                'unique': True  
            },
        ]
    }
    def get_bucket_path(self):
        return f"book_{self.book_id}/{self.id}_{self.chapter_name}"
    def get_pdf_path(self):
        return f"book_{self.book_id}_chapter_{self.id}.pdf"

Chapter.register_delete_rule(Page, 'chapter', db.CASCADE)
