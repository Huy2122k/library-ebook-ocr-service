# from .auth import LoginApi, SignupApi
from .book import BookApi, BooksApi
from .chapter import ChapterApi, ChapterGetAllApi, ChaptersApi
from .ocr import OcrApi
from .page import PageApi, PagesApi
from .urls import PreSignUrlApi

# from .reset_password import ForgotPassword, ResetPassword


def initialize_routes(api):

    api.add_resource(ChaptersApi, '/api/chapters')
    api.add_resource(ChapterApi, '/api/chapters/<chapter_id>')

    api.add_resource(PagesApi, '/api/pages')
    api.add_resource(PageApi, '/api/page/<page_id>')

    api.add_resource(BooksApi, '/api/books')
    api.add_resource(BookApi, '/api/books/<book_id>')
    api.add_resource(ChapterGetAllApi, '/api/chapter_meta/<chapter_id>')
    
    api.add_resource(OcrApi, '/api/ocr')
    api.add_resource(PreSignUrlApi, '/api/presigned')


    # api.add_resource(SignupApi, '/api/auth/signup')
    # api.add_resource(LoginApi, '/api/auth/login')

    # api.add_resource(ForgotPassword, '/api/auth/forgot')
    # api.add_resource(ResetPassword, '/api/auth/reset')
