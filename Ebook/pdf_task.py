import copy
import io
import os
import traceback
from io import BytesIO

import fitz
import pytesseract
import requests
from celery import Celery
from celery.utils.log import get_task_logger
from cloud.minio_utils import config, minio_client
from database.models import *
from gtts import gTTS
from jobs.pdf_utils import *
from PIL import Image
from pydub import AudioSegment

# If you don't have tesseract executable in your PATH, include the following:
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

# cache = redis.Redis(host='localhost', port=6379, db=0,  password ="eYVX7EwVmmxKPCDmwMtyKVge8oLd2t81")

logger = get_task_logger(__name__)


APP_HOST = 'http://server:3500'


pdf_app = Celery('pdf_process',
             broker='amqp://admin:mypass@rabbit:5672',
             backend='mongodb://mongodb-docker:27017/mydb')



@pdf_app.task()
def split_page_pdf(page_id, page_number,page_pdf_object_key, page_img_object_key, book_pdf_object_key):
    try:
        # caching is error now
        # book_cached = cache.get(book_pdf_object_key)
        cache_path = f"cache/{book_pdf_object_key}"
        if not os.path.exists(cache_path):
            response = minio_client.get_object(config["BASE_BUCKET"], book_pdf_object_key)
            bookDoc = fitz.open("pdf", response.data)
            print("CACHED!")
            bookDoc.save(cache_path)
        else:
            bookDoc = fitz.open(cache_path)
        # if book_cached is None:
        #     bookDoc = fitz.open("pdf", response.data)
        #     pickled_object = pickle.dumps(bookDoc)
        #     cache.set(book_pdf_object_key, pickled_obje
        # else:
        #     bookDoc = pickle.loads(book_cached)
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
        return {"page_id": page_id, "image_status": Status.READY, "pdf_status": Status.READY}
    except Exception as e:
        on_error(e)
        requests.put(f"{APP_HOST}/api/page/{page_id}", json = {"pdf_status": Status.ERROR})
        requests.put(f"{APP_HOST}/api/page/{page_id}", json = {"image_status": Status.ERROR})
        return {"page_id": page_id, "image_status": Status.ERROR, "pdf_status": Status.ERROR}
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
            info = {'index': sentenceIdx, 'bounding_box': boundingBox, 'text': text}
            metadata.append(info)
        x = requests.put(f"{APP_HOST}/api/page/{page_id}", json = {"sentences": metadata, "bounding_box_status": Status.READY})
        return x.json()
    except Exception as e:
        on_error(e)
        x = requests.put(f"{APP_HOST}/api/page/{page_id}", json = {"bounding_box_status": Status.ERROR})
        return {"page_id": page_id, "bounding_box_status": Status.ERROR}

@pdf_app.task()
def merge_chapter_pdf(chapter_id, page_pdf_object_key_list, chapter_pdf_object_key):
    try:
        chapter = requests.get(f"{APP_HOST}/api/chapters/{chapter_id}").json()
        if chapter["status"]["pdf_status"] != "ready":
            return f"chapter {chapter_id} pdf merge incomplete!"
        logger.info(f"chapter {chapter_id} is merging pdf")
        page_pdf_object_key_list = json.loads(page_pdf_object_key_list)
        chapter_doc = fitz.open()
        for object_key in page_pdf_object_key_list:
            response = minio_client.get_object(config["BASE_BUCKET"], object_key)
            doc = fitz.open("pdf", response.data)
            chapter_doc.insert_pdf(doc)
        pdf_data = chapter_doc.tobytes()
        raw_pdf = BytesIO(pdf_data)
        raw_pdf_size = raw_pdf.getbuffer().nbytes
        minio_client.put_object(bucket_name = config['BASE_BUCKET'], 
                                object_name = chapter_pdf_object_key, 
                                data = raw_pdf, 
                                length= raw_pdf_size,
                                content_type = 'application/pdf')
        return f"chapter {chapter_id} 's pdf is merged successfully!"
    except Exception as e:
        on_error(e)
        return f"chapter {chapter_id}  pdf merge is error!"

@pdf_app.task()
def concat_audio(chapter_id, page_audio_object_key_list, chapter_audio_object_key):
    try:
        chapter = requests.get(f"{APP_HOST}/api/chapters/{chapter_id}").json()
        if chapter["status"]["audio_status"] != "ready":
            return f"chapter {chapter_id} audio concat incomplete!"
        audio_segment_list = []
        page_audio_object_key_list = json.loads(page_audio_object_key_list)
        for object_key in page_audio_object_key_list:
            response = minio_client.get_object(config["BASE_BUCKET"], object_key)
            audio_segment_list.append(AudioSegment.from_file(BytesIO(response.data), format="mp3"))
        audio = merge_audio_segments(audio_segment_list)
        raw_audio = BytesIO()
        audio.export(raw_audio, format="mp3")
        raw_audio_size = raw_audio.getbuffer().nbytes
        minio_client.put_object(bucket_name = config['BASE_BUCKET'], 
                                object_name = chapter_audio_object_key, 
                                data = raw_audio, 
                                length= raw_audio_size,
                                content_type = 'audio/mpeg')
        return "success"
    except Exception as e:
        on_error(e)
        return f"chapter {chapter_id}  audio merge is error!"

@pdf_app.task()
def create_ocr_page(page_id, img_object_key, pdf_object_key):
    try:
        response = minio_client.get_object(config["BASE_BUCKET"], img_object_key)
        im = Image.open(response)
        pdf = pytesseract.image_to_pdf_or_hocr(im, extension='pdf')
        raw_pdf = io.BytesIO(pdf)
        raw_pdf_size = raw_pdf.getbuffer().nbytes
        minio_client.put_object(bucket_name = config['BASE_BUCKET'], 
                                object_name = pdf_object_key, 
                                data = raw_pdf, 
                                length= raw_pdf_size,
                                content_type = 'application/pdf')
        x = requests.put(f"{APP_HOST}/api/page/{page_id}", json = {"pdf_status": Status.READY})
        return x.json()
    except Exception as e:
        on_error(e) #
        x = requests.put(f"{APP_HOST}/api/page/{page_id}", json = {"pdf_status": Status.ERROR})
        return {"page_id": page_id, "pdf_status": Status.ERROR}

def on_error(e):
    with open('errors.log', 'a') as fh:
        print('--\n\n{0}'.format(traceback), file=fh)
        traceback.print_exc(file=fh)
    print(e)
    


def convert_text_to_pydub_audio_segment(text, language="vi"):
    gtts_object = gTTS(text = text, 
                       lang = language,
                       slow = False)
    audio_bytes = BytesIO()
    gtts_object.write_to_fp(audio_bytes)
    audio_bytes.seek(0)
    return AudioSegment.from_file(audio_bytes, format="mp3")

def merge_audio_segments(audio_segment_list):
    main_audio = audio_segment_list[0]
    for segment in audio_segment_list[1:]:
        main_audio += segment
    return main_audio

@pdf_app.task()
def text_to_speech(page_id, page_audio_object_key):
    try:
        get_response = requests.get(f"{APP_HOST}/api/page/{page_id}")
        sentence_list = json.loads(json.dumps(get_response.json()['sentences']))
        audio_segment_list = []
        for sentence in sentence_list:
            text = sentence['text']
            if not text:
                continue
            audio_segment = convert_text_to_pydub_audio_segment(text)
            audio_segment_list.append(audio_segment)
            sentence["audio_timestamp"] = audio_segment.duration_seconds
            del sentence["page"]
        get_response = requests.put(f"{APP_HOST}/api/page/{page_id}", json={"sentences": sentence_list})
        if len(audio_segment_list) > 0:
            main_audio = merge_audio_segments(audio_segment_list)
            raw_audio = BytesIO()
            main_audio.export(raw_audio, format="mp3")
            raw_audio_size = raw_audio.getbuffer().nbytes
            minio_client.put_object(bucket_name = config['BASE_BUCKET'], 
                                    object_name = page_audio_object_key, 
                                    data = raw_audio, 
                                    length= raw_audio_size,
                                    content_type = 'audio/mpeg')
        update_response = requests.put(f"{APP_HOST}/api/page/{page_id}", json = {"audio_status": Status.READY})
        return {"page_id": page_id, "audio_status": Status.READY}
    except Exception as e:
        on_error(e)
        requests.put(f"{APP_HOST}/api/page/{page_id}", json = {"audio_status": Status.ERROR})
        return {"page_id": page_id, "audio_status": Status.ERROR}