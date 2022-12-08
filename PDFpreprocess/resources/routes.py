from .pdf import BBCreateApi, PdfConverterApi, SplitBookApi


def initialize_routes(api):
    api.add_resource(BBCreateApi, '/api/pdf')
    api.add_resource(PdfConverterApi, '/api/convert_pdf')
    api.add_resource(SplitBookApi, '/api/split_book')
