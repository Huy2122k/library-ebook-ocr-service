# from .auth import LoginApi, SignupApi
from .book import BookApi, BooksApi
from .chapter import ChapterApi, ChapterGetAllApi, ChaptersApi
from .page import PageApi, PagesApi
from .task import TaskApi
from .urls import PreSignUrlApi

# from .reset_password import ForgotPassword, ResetPassword


class AppRoutes():

    def __init__(self, api):
        self.api = api

    def init_routes(self):
        self.api.add_resource(ChaptersApi, '/api/chapters')
        self.api.add_resource(ChapterApi, '/api/chapters/<chapter_id>')

        self.api.add_resource(PagesApi, '/api/pages')
        self.api.add_resource(PageApi, '/api/page/<page_id>')

        self.api.add_resource(BooksApi, '/api/books')
        self.api.add_resource(BookApi, '/api/books/<book_id>')
        self.api.add_resource(ChapterGetAllApi, '/api/chapter_meta/<chapter_id>')
        
        self.api.add_resource(TaskApi, '/api/ocr')
        self.api.add_resource(PreSignUrlApi, '/api/presigned')


        # self.api.add_resource(SignupApi, '/api/auth/signup')
        # self.api.add_resource(LoginApi, '/api/auth/login')

        # self.api.add_resource(ForgotPassword, '/api/auth/forgot')
        # self.api.add_resource(ResetPassword, '/api/auth/reset')
