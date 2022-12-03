import os

import fitz
import pytesseract
from PIL import Image

from cloud.minio_utils import config, minio_client

# If you don't have tesseract executable in your PATH, include the following:
pytesseract.pytesseract.tesseract_cmd = r'D:/Tesseract/tesseract'

# Get a searchable PDF
# with open('test-batch-chines.pdf', 'a+b') as f:
#     f.write(pdf) # pdf type is bytes by default
# Get data of an object.


def add_to_pdf_merge(pdf, output):
    if os.path.isfile(output):
        z = fitz.open(output)
    else:
        z = fitz.open() # an empty pdf file is opened
    x = fitz.open('pdf',pdf) # open the bytes in pdf
    z.insert_pdf(x, from_page=0, to_page=0) # merge pdfs into single file
    if os.path.isfile(output):
        z.save(output, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
    else:
        z.save(output)
def create_ocr_page(chapter_path, object_key):
    try:
        response = minio_client.get_object(config["BASE_BUCKET"], object_key)
        im = Image.open(response)
        pdf = pytesseract.image_to_pdf_or_hocr(im, extension='pdf',lang="vie")
        output = f"ocr/output_temp/{chapter_path}.pdf"
        add_to_pdf_merge(pdf, output)
    except Exception as e:
        print(e)
        return None
    finally:
        response.close()
    return output



