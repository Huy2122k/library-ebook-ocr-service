# from .auth import LoginApi, SignupApi
from .chapter import ChapterApi, ChaptersApi
from .ocr import OcrApi
from .page import PageApi, PagesApi

# from .reset_password import ForgotPassword, ResetPassword


def initialize_routes(api):

    api.add_resource(ChaptersApi, '/api/chapters')
    api.add_resource(ChapterApi, '/api/chapters/<chapter_id>')

    api.add_resource(PagesApi, '/api/pages')
    api.add_resource(PageApi, '/api/pages/<page_id>')
    
    api.add_resource(OcrApi, '/api/ocr')

    # api.add_resource(SignupApi, '/api/auth/signup')
    # api.add_resource(LoginApi, '/api/auth/login')

    # api.add_resource(ForgotPassword, '/api/auth/forgot')
    # api.add_resource(ResetPassword, '/api/auth/reset')
