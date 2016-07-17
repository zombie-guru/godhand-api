import os
import tempfile

from cornice import Service
from pyramid.httpexceptions import HTTPNotFound
import colander as co
import couchdb.http

from godhand import bookextractor
from .utils import PaginationSchema
from .utils import paginate_query


class BookPathSchema(co.MappingSchema):
    book = co.SchemaNode(
        co.String(),
        location='path',
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
                {"id": "myid", "title": "My Book Title"}
            ],
            "offset": 0,
            "total": 1
        }

    """
    query = '''function(doc) {
        emit({
            id: doc._id,
            title: doc.title
        })
    }
    '''
    obj = paginate_query(request, query, 'books')
    return obj


@books.post(content_type=('multipart/form-data',))
def upload_books(request):
    """ Create book and return unique ids.
    """
    book_ids = []
    for key, value in request.POST.items():
        basedir = tempfile.mkdtemp(dir=request.registry['godhand:books_path'])
        extractor_cls = bookextractor.from_filename(value.filename)
        extractor = extractor_cls(value.file, basedir)
        book = {
            'title': 'Untitled',
            'path': basedir,
            'pages': [{
                'path': page,
            } for page, mimetype in extractor.iter_pages()]
        }
        _id, _rev = request.registry['godhand:db'].save(book)
        book_ids.append(_id)
    return {'books': book_ids}


@book.get()
def get_book(request):
    """ Get a book by ID.

    .. code-block:: js

        {
            "id": "myuniqueid",
            "title": "My Book Title",
            "pages": [
                {"url": "http://url.to.page0.jpg"}
            ]
        }

    """
    book_id = request.validated['book']
    db = request.registry['godhand:db']
    try:
        doc = db[book_id]
    except couchdb.http.ResourceNotFound:
        raise HTTPNotFound(book_id)
    else:
        return {
            'id': doc['_id'],
            'title': doc['title'],
            'pages': [{
                'url': request.static_url(
                    os.path.join(doc['path'], x['path'])),
            } for x in doc['pages']]
        }
