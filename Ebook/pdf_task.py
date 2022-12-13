import io
import os
import pickle
import sys
import traceback

import fitz
import redis
import requests
from celery import Celery
from celery.utils.log import get_task_logger
from cloud.minio_utils import config, minio_client
from database.models import *
from jobs.pdf_utils import *

cache = redis.Redis(host='localhost', port=6379, db=0,  password ="eYVX7EwVmmxKPCDmwMtyKVge8oLd2t81")

logger = get_task_logger(__name__)


APP_HOST = 'http://localhost:3500'


pdf_app = Celery('pdf_process',
             broker='amqp://admin:mypass@localhost:5672',
             backend='mongodb://localhost:27017/mydb')



@pdf_app.task()
def split_page_pdf(page_id, page_number,page_pdf_object_key, page_img_object_key, book_pdf_object_key):
    try:
        # caching is error now
        # book_cached = cache.get(book_pdf_object_key)
        # if book_cached is None:
        #     response = minio_client.get_object(config["BASE_BUCKET"], book_pdf_object_key)
        #     bookDoc = fitz.open("pdf", response.data)
        #     pickled_object = pickle.dumps(bookDoc)
        #     cache.set(book_pdf_object_key, pickled_object)
        #     print("CACHED!")
        # else:
        #     bookDoc = pickle.loads(book_cached)
        response = minio_client.get_object(config["BASE_BUCKET"], book_pdf_object_key)
        bookDoc = fitz.open("pdf", response.data)
        page_data = bookDoc[page_number]

        page_data_pdf = fitz.open() # an empty pdf file is opened
        page_data_pdf.insert_pdf(bookDoc, from_page=page_number, to_page=page_number)

        data = page_data_pdf.tobytes()
        raw_pdf = io.BytesIO(data)
        raw_pdf_size = raw_pdf.getbuffer().nbytes
        minio_client.put_object(bucket_name = config['BASE_BUCKET'], 
                                object_name = page_pdf_object_key, 
                                data = raw_pdf, 
                                length= raw_pdf_size,
                                content_type = 'application/pdf')
        x = requests.put(f"{APP_HOST}/api/page/{page_id}", json = {"pdf_status": Status.READY})
        logger.info(f"page {page_id} pdf create", x.status_code)
        pix = page_data.get_pixmap()
        data = pix.pil_tobytes(format="png", optimize=True)
        raw_img = io.BytesIO(data)
        raw_img_size = raw_img.getbuffer().nbytes
        minio_client.put_object(bucket_name = config['BASE_BUCKET'], 
                                object_name = page_img_object_key, 
                                data = raw_img, 
                                length= raw_img_size,
                                content_type = 'image/png')
        y = requests.put(f"{APP_HOST}/api/page/{page_id}", json = {"image_status": Status.READY})
        logger.info(f"page {page_id} image create", x.status_code)
        return [x.status_code, y.status_code]
    except Exception as e:
        with open('errors.log', 'a') as fh:
            print('--\n\n{0}'.format(traceback), file=fh)
            traceback.print_exc(file=fh)
        requests.put(f"{APP_HOST}/api/page/{page_id}", json = {"pdf_status": Status.ERROR})
        requests.put(f"{APP_HOST}/api/page/{page_id}", json = {"image_status": Status.ERROR})
# @pdf_app.task()
# def create_page_image(page_data, page_img_object_key, page_id):
#     pix = page_data.get_pixmap()
#     data = pix.pil_tobytes(format="png", optimize=True)
#     raw_img = io.BytesIO(data)
#     raw_img_size = raw_img.getbuffer().nbytes
#     minio_client.put_object(bucket_name = config['BASE_BUCKET'], 
#                             object_name = page_img_object_key, 
#                             data = raw_img, 
#                             length= raw_img_size,
#                             content_type = 'image/png')
#     x = requests.put(f"{APP_HOST}/api/page/{page_id}", json = {"image_status": Status.READY})
#     logger.info(f"page {page_id} image create", x.status)
#     return x.status


@pdf_app.task()
def log_error(request, exc, traceback):
    with open('errors.log', 'a') as fh:
        print('--\n\n{0} {1} {2}'.format(
            request.id, exc, traceback), file=fh)

@pdf_app.task()
def page_error(status_type,page_id):
    x = requests.put(f"{APP_HOST}/api/page/{page_id}", json = {status_type: Status.ERROR})
    return x.status_code


@pdf_app.task()
def bounding_box_preprocess(page_id, pdf_object_key):
    logger.info(f"page {page_id} is creating bounding box")
    try:
        response = minio_client.get_object(config["BASE_BUCKET"], pdf_object_key)
        doc = fitz.open("pdf", response.data)
        page = doc[0]
        sentences = read_page(page)
        metadata = []
        for (sentenceIdx, wordList) in enumerate(sentences):
            startPoints, endPoints = merge_bounding_box(wordList)
            text = get_text(wordList)
            boundingBox = []
            for (startPoint, endPoint) in zip(startPoints, endPoints):
                boundingBox.append(convert_bb_type(startPoint, endPoint))
            info = {'index': sentenceIdx, 'boundingBox': boundingBox, 'text': text}
            metadata.append(info)
            x = requests.put(f"{APP_HOST}/api/page/{page_id}", json = {"sentences": metadata})
        return x.status
    except Exception as e:
        x = requests.put(f"{APP_HOST}/api/page/{page_id}", json = {"ocr_status": Status.ERROR})