import io

import fitz
import nltk

nltk.download('punkt')

from autocorrect import Speller
from langdetect import detect
from nltk.tokenize import sent_tokenize


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

def sentences_extract(region_words):
    # Tạo danh sách các từ đơn lẻ
    word_list_only = [word[4] for word in region_words]
    # Gộp danh sách từ thành một câu
    text = " ".join(word_list_only)
    # Phân đoạn câu
    sentences = sent_tokenize(text)
    result = []
    index = 0
    for s in sentences:
        temp_words = s.split()
        tuples = [region_words[i] for i in range(index, index + len(temp_words)) if i < len(region_words)]
        result.append(tuples)
        index += len(temp_words)
    return result

def read_page_new(page):
    words = page.get_text("words", sort=True)
    blocks = page.get_text("blocks", sort=True)
    # find avg height
    line_heights = [(blocks[idx + 1][1] - block[3]) for idx, block in enumerate(blocks) if idx < len(blocks)-1]
    line_heights = [height for height in line_heights if height > 0]
    regions_words = [words]

    if len(line_heights) > 0:
        # Layout Split
        regions_words = []
        temp = []
        avg = sum(line_heights)/len(line_heights)
        for (idx, word) in enumerate(words):
            temp.append(word)
            if idx < len(words)-1 and word[5] < words[idx+1][5]:
                if (words[idx+1][1] - word[3]) > 3*avg:
                    regions_words.append(temp)
                    temp=[]
            if idx == len(words) - 1:
                regions_words.append(temp)

    sentences = []

    for region_words in regions_words:
        sentences += sentences_extract(region_words)

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
    text = " ".join([word[4] for word in wordList])
    # spell correction
    try:
        language = "en" if str(detect(text)) == "en" else "vi"
    except:
        language = 'en'
        pass
    # only auto correct english  
    if language == "en":
        spell = Speller(only_replacements=True, lang=language)
        text = spell(text)

    return text

# Hợp nhất bounding box của các từ trong câu thành các bounding box của các dòng
def merge_bounding_box(wordList):
    startPoints = [(word[0], word[1]) for word in wordList]
    endPoints = [(word[2], word[3]) for word in wordList]
    if len(wordList) == 0:
        return [], [], []
    # Lưu nhóm các bounding box nằm trên cùng 1 dòng
    lineGroupStartPoints=[]
    lineGroupEndPoints=[]
    lineGroupTexts =[]

    tempStartPoints=[startPoints[0]]
    tempEndPoints=[endPoints[0]]
    tempTexts = wordList[0][4]
    for i in range((len(startPoints)-1)):
        if startPoints[i+1][0]>startPoints[i][0]:
            tempStartPoints.append(startPoints[i+1])
            tempEndPoints.append(endPoints[i+1])
            tempTexts += (" " + wordList[i+1][4])
        else:
            lineGroupStartPoints.append(tempStartPoints)
            lineGroupEndPoints.append(tempEndPoints)
            lineGroupTexts.append(tempTexts)
            tempStartPoints=[startPoints[i+1]]
            tempEndPoints=[endPoints[i+1]]
            tempTexts=wordList[i+1][4]
        if i >= len(startPoints)-2:
            lineGroupStartPoints.append(tempStartPoints)
            lineGroupEndPoints.append(tempEndPoints)
            lineGroupTexts.append(tempTexts)
    
    # Lưu bounding box sau khi đã được merge
    lineStartPoints=[]
    lineEndPoints=[]
    for (listStartPoints, listEndPoints) in zip(lineGroupStartPoints, lineGroupEndPoints):
        startPoint, endPoint = find_bounding_box(listStartPoints, listEndPoints)
        lineStartPoints.append(startPoint)
        lineEndPoints.append(endPoint)
    
    return lineStartPoints, lineEndPoints, lineGroupTexts

# Chuyển thông tin bounding box từ top left/bottom right
# sang x_top_left/y_top_left/width/height
def convert_bb_type(startPoint, endPoint):
    return {'x': startPoint[0], 'y': startPoint[1], 'width': endPoint[0]-startPoint[0], 'height': endPoint[1]-startPoint[1]}
