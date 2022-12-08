import fitz
from cloud.minio_utils import config, minio_client
import io

# Đọc 1 trang
def read_page(page):
    # Trích rút các câu
    sentences = []
    temp = []
    words = page.get_text("words", sort=False)
    for (idx, word) in enumerate(words):
        temp.append(word)
        if word[4][-1] in ['.', '!', '?']:
            sentences.append(temp)
            temp=[]
        if idx == len(words)-1:
            sentences.append(temp)
    return sentences

# Hàm tìm bounding box bao list các bounding box
def find_bounding_box(listStartPoints, listEndPoints):
    x0 = listStartPoints[0][0]
    y0 = min([i[1] for i in listStartPoints])
    x1 = listEndPoints[-1][0]
    y1 = max([i[1] for i in listEndPoints])
    return (round(x0), round(y0)), (round(x1), round(y1))

# Lấy các câu
def get_text(wordList):
    text = ""
    for (idx, word) in enumerate(wordList):
        text+=word[4]+" "
        if idx == len(wordList)-1:
            text+=word[4]
    return text

# Hợp nhất bounding box của các từ trong câu thành các bounding box của các dòng
def merge_bounding_box(wordList):
    startPoints = [(word[0], word[1]) for word in wordList]
    endPoints = [(word[2], word[3]) for word in wordList]

    # Lưu nhóm các bounding box nằm trên cùng 1 dòng
    lineGroupStartPoints=[]
    lineGroupEndPoints=[]

    tempStartPoints=[startPoints[0]]
    tempEndPoints=[endPoints[0]]
    for i in range((len(startPoints)-1)):
        if startPoints[i+1][0]>startPoints[i][0]:
            tempStartPoints.append(startPoints[i+1])
            tempEndPoints.append(endPoints[i+1])
        else:
            lineGroupStartPoints.append(tempStartPoints)
            lineGroupEndPoints.append(tempEndPoints)
            tempStartPoints=[startPoints[i+1]]
            tempEndPoints=[endPoints[i+1]]
        if i == len(startPoints)-2:
            lineGroupStartPoints.append(tempStartPoints)
            lineGroupEndPoints.append(tempEndPoints)
    
    # Lưu bounding box sau khi đã được merge
    lineStartPoints=[]
    lineEndPoints=[]
    for (listStartPoints, listEndPoints) in zip(lineGroupStartPoints, lineGroupEndPoints):
        startPoint, endPoint = find_bounding_box(listStartPoints, listEndPoints)
        lineStartPoints.append(startPoint)
        lineEndPoints.append(endPoint)
    
    return lineStartPoints, lineEndPoints

# Chuyển thông tin bounding box từ top left/bottom right
# sang x_top_left/y_top_left/width/height
def convert_bb_type(startPoint, endPoint):
    return {'x': startPoint[0], 'y': startPoint[1], 'width': endPoint[0]-startPoint[0], 'height': endPoint[1]-startPoint[1]}

def bounding_box_preprocess(pdf_object_key):
    try:
        response = minio_client.get_object(config["BASE_BUCKET"], pdf_object_key)
        print(type(response))
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
        
    except Exception as e:
        print(e)
        return None
    finally:
        response.close()
    return metadata

def convert_pdf_to_image(pdf_object_key, img_object_key):
    try:
        response = minio_client.get_object(config["BASE_BUCKET"], pdf_object_key)
        doc = fitz.open("pdf", response.data)
        pix = doc[0].get_pixmap()
        data = pix.pil_tobytes(format="png", optimize=True)
        raw_img = io.BytesIO(data)
        raw_img_size = raw_img.getbuffer().nbytes
        minio_client.put_object(bucket_name = config['BASE_BUCKET'], 
                                object_name = img_object_key, 
                                data = raw_img, 
                                length= raw_img_size,
                                content_type = 'image/png')
    except Exception as e:
        print(e)
        return None
    finally:
        response.close()
    return 'ok'

def split_book(book_pdf_object_key, from_page, to_page, chapter_pdf_object_key):
    try:
        response = minio_client.get_object(config["BASE_BUCKET"], book_pdf_object_key)
        bookDoc = fitz.open("pdf", response.data)
        chapterDoc = fitz.open()
        chapterDoc.insert_pdf(bookDoc, from_page-1, to_page-1)
        data = chapterDoc.tobytes()
        raw_pdf = io.BytesIO(data)
        raw_pdf_size = raw_pdf.getbuffer().nbytes
        minio_client.put_object(bucket_name = config['BASE_BUCKET'], 
                                object_name = chapter_pdf_object_key, 
                                data = raw_pdf, 
                                length= raw_pdf_size,
                                content_type = 'application/pdf')
    except Exception as e:
        print(e)
        return None
    finally:
        response.close()
    return 'ok'