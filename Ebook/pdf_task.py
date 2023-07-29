import copy
import io
import json
import os
import traceback
from io import BytesIO

import fitz
import pytesseract
import requests
from celery import Celery
from celery.utils.log import get_task_logger
from cloud.minio_utils import config, minio_client
from database.models import Status
# for google TTS API
from google.cloud import texttospeech
from google.oauth2 import service_account
from jobs.post_process import *
from jobs.pre_process import deskew_image
from PIL import Image
from pydub import AudioSegment

logger = get_task_logger(__name__)

google_credentials = service_account.Credentials.from_service_account_file('credentials/library-audio-book-cec98cdbbdbd.json')
text_to_speech_client = texttospeech.TextToSpeechClient(credentials=google_credentials)

pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

APP_HOST = 'http://server:3600'
pdf_app = Celery('pdf_process',
             broker='amqp://admin:mypass@rabbit:5672',
             backend='mongodb://mongodb-docker:27017/mydb')



@pdf_app.task()
def split_page_pdf(page_id, page_number,page_pdf_object_key, page_img_object_key, book_pdf_object_key):
    try:
        # caching 
        cache_path = f"cache/{book_pdf_object_key.split('/')[-1]}"
        if not os.path.exists(cache_path):
            response = minio_client.get_object(config["BASE_BUCKET"], book_pdf_object_key)
            bookDoc = fitz.open("pdf", response.data)
            print("CACHED! ", book_pdf_object_key)
            bookDoc.save(cache_path)
        else:
            bookDoc = fitz.open(cache_path)
        page_data = bookDoc[page_number]

        page_data_pdf = fitz.open() # an empty pdf file is opened
        page_data_pdf.insert_pdf(bookDoc, from_page=page_number, to_page=page_number)

        # Resize PDF to A4
        resize_doc = fitz.open()  # new empty PDF
        page = resize_doc.new_page()  # new page in A4 format
        page.show_pdf_page(page.rect, page_data_pdf, 0)

        data = resize_doc.tobytes()
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
        sentences = read_page_new(page)
        metadata = []
        for (sentenceIdx, wordList) in enumerate(sentences):
            startPoints, endPoints, ocr_texts = merge_bounding_box(wordList)
            text = get_text(wordList)
            boundingBox = []
            for (startPoint, endPoint) in zip(startPoints, endPoints):
                boundingBox.append(convert_bb_type(startPoint, endPoint))
            info = {'index': sentenceIdx, 'bounding_box': boundingBox, 'text': text, 'ocr_texts': ocr_texts}
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
            try:
                response = minio_client.get_object(config["BASE_BUCKET"], object_key)
            except Exception as e:
                continue
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
        im = deskew_image(im)
        # Tesseract 
        pdf = pytesseract.image_to_pdf_or_hocr(im, extension='pdf', lang='vie+eng', config=f'--psm 11')
        doc = fitz.open("pdf", pdf)
        resize_doc = fitz.open()  # new empty PDF
        page = resize_doc.new_page()  # new page in A4 format
        page.show_pdf_page(page.rect, doc, 0)

        pdf_data = resize_doc.tobytes()
        raw_pdf = io.BytesIO(pdf_data)
        raw_pdf_size = raw_pdf.getbuffer().nbytes
        minio_client.put_object(bucket_name = config['BASE_BUCKET'], 
                                object_name = pdf_object_key, 
                                data = raw_pdf, 
                                length= raw_pdf_size,
                                content_type = 'application/pdf')

        pix = resize_doc[0].get_pixmap()
        data = pix.pil_tobytes(format="png", optimize=True)
        raw_img = io.BytesIO(data)
        raw_img_size = raw_img.getbuffer().nbytes

        minio_client.put_object(bucket_name = config['BASE_BUCKET'], 
                        object_name = img_object_key, 
                        data = raw_img, 
                        length= raw_img_size,
                        content_type = 'image/png')

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
    

def run_google_text_to_speech(text, lang='en'):
    synthesis_input = texttospeech.SynthesisInput(text=text)
    # Build the voice request, select the language code ("en-US") and the ssml
    # voice gender ("neutral")
    params_voice = {
        "language_code": "en-US",
        "name": "en-US-Standard-H"
    }
    if lang =='vi':
        params_voice = {
            "language_code": "vi-VN",
            "name": "vi-VN-Standard-A"
        }

    voice = texttospeech.VoiceSelectionParams(**params_voice)
    # Select the type of audio file you want returned
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    # Perform the text-to-speech request on the text input with the selected
    # voice parameters and audio file type
    response = text_to_speech_client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    audio_bytes = BytesIO(response.audio_content)
    audio_segment = AudioSegment.from_file(audio_bytes, format="mp3")
    
    return audio_segment

def merge_audio_segments(audio_segment_list):
    if len(audio_segment_list) > 0:
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
        sentence_new_list = []
        for sentence in sentence_list:
            text = sentence['text']
            language = sentence['language_detect']
            del sentence["language_detect"]
            del sentence["page"]
            del sentence["_id"]
            del sentence["text_search"]
            if not text or text.strip() == '' :
                continue
            audio_segment = run_google_text_to_speech(text, language)
            audio_segment_list.append(audio_segment)
            sentence["audio_timestamp"] = audio_segment.duration_seconds
            sentence_new_list.append(sentence)
            
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
        update_response = requests.put(f"{APP_HOST}/api/page/{page_id}", json = {"sentences": sentence_new_list, "audio_status": Status.READY})
        return {"page_id": page_id, "audio_status": Status.READY}
    except Exception as e:
        on_error(e)
        requests.put(f"{APP_HOST}/api/page/{page_id}", json = {"audio_status": Status.ERROR})
        return {"page_id": page_id, "audio_status": Status.ERROR}
    