import os

import fitz
import pytesseract
from PIL import Image
import io

from cloud.minio_utils import config, minio_client

# If you don't have tesseract executable in your PATH, include the following:
# MacOS
# pytesseract.pytesseract.tesseract_cmd = r'/opt/homebrew/Cellar/tesseract/5.2.0/bin/tesseract'
# Windows
pytesseract.pytesseract.tesseract_cmd = r'D:/Tesseract/tesseract'

def create_ocr_page(img_object_key, pdf_object_key):
    try:
        response = minio_client.get_object(config["BASE_BUCKET"], img_object_key)
        im = Image.open(response)
        print(type(im))
        pdf = pytesseract.image_to_pdf_or_hocr(im, extension='pdf',lang="vie")
        raw_pdf = io.BytesIO(pdf)
        raw_pdf_size = raw_pdf.getbuffer().nbytes
        minio_client.put_object(bucket_name = config['BASE_BUCKET'], 
                                object_name = pdf_object_key, 
                                data = raw_pdf, 
                                length= raw_pdf_size,
                                content_type = 'application/pdf')
    except Exception as e:
        print(e)
        return None
    finally:
        response.close()
    return 'ok'



