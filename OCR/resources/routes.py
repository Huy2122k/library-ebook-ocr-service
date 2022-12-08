from .ocr import OcrApi


def initialize_routes(api):
    api.add_resource(OcrApi, '/api/ocr')
