from cornice import Service
from pyramid.response import FileResponse
from pyramid.httpexceptions import HTTPNotFound
import colander as co

from godhand import bookextractor
from godhand.models import DB
from godhand.models import Book
from godhand.models import Page
from .utils import PaginationSchema
from .utils import paginate_query
from .utils import sqlalchemy_path_schemanode


class BookPathSchema(co.MappingSchema):
    book = sqlalchemy_path_schemanode(Book)


class BookPagePathSchema(BookPathSchema):
    page = co.SchemaNode(
        co.Integer(),
        location='path',
        validator=co.Range(min=0),
    )


books = Service(
    name='books',
    path='/books',
)
book = Service(
    name='book',
    path='/books/{book}',
    schema=BookPathSchema,
)
book_pages = Service(
    name='book_pages',
    path='/books/{book}/pages',
    schema=BookPathSchema,
)
book_page = Service(
    name='books_page',
    path='/books/{book}/pages/{page}',
    schema=BookPagePathSchema,
)


def prepare_book(book):
    return {
        'id': book.id,
        'title': book.title,
        'pages': [x.id for x in book.pages],
    }


def prepare_page(page):
    return {
        'id': page.id,
        'mimetype': page.mimetype,
    }


@books.get(schema=PaginationSchema)
def get_books(request):
    """ Get all books.

    .. source-code:: js

        {
            "books": [
                {
                    "id": 1,
                    "title": "Beserk",
                    "pages": [1, 2, 3]
                }
            ]
        }
    """
    query = DB.query(Book)
    return paginate_query(request, query, prepare_book, 'books')


@books.post(content_type=('multipart/form-data',))
def upload_book(request):
    for key, value in request.POST.items():
        extractor_cls = bookextractor.from_filename(value.filename)
        book = Book.create(
            title='Untitled', f=value.file, extractor_cls=extractor_cls,
            book_path=request.registry['godhand:book_path'],
        )
    return prepare_book(book)


@book.get()
def get_book(request):
    return prepare_book(request.validated['book'])


class GetBookPagesSchema(BookPathSchema, PaginationSchema):
    pass


@book_pages.get(schema=GetBookPagesSchema)
def get_book_pages(request):
    """ Get pages for a book.

    .. source-code:: js

        {
            "pages": [
                {"id": 1, "mimetype": "images/png"}
            ]
        }
    """
    book = request.validated['book']
    query = DB.query(Page).filter(Page.book_id == book.id).order_by(Page.id)
    return paginate_query(request, query, prepare_page, 'pages')


@book_page.get(accept=('images/*',))
def get_book_page(request):
    """ Get a book page content by offset. Starts at 0.
    """
    book = request.validated['book']
    page = DB.query(
        Page
    ).filter(
        Page.book_id == book.id
    ).order_by(
        Page.id
    ).offset(request.validated['page']).first()
    if page is None:
        raise HTTPNotFound()
    return FileResponse(
        path=page.path,
        request=request,
        content_type=page.mimetype,
    )
