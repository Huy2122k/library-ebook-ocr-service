import numpy as np
from deskew import determine_skew
from PIL import Image


def determine_skew_pillow(img):
    # Chuyển ảnh PIL thành numpy array để phù hợp với deskew
    grayscale = np.array(img.convert('L'))
    # Xác định góc xoay của ảnh
    angle = determine_skew(grayscale, angle_pm_90=True)
    return angle

def deskew_image(img):
    # Xác định góc xoay
    angle = determine_skew_pillow(img)
    # Xoay ảnh theo góc đã xác định
    rotated_img = img.rotate(angle, resample=Image.BICUBIC, expand=False)
    return rotated_img