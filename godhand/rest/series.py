from cornice import Service
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.httpexceptions import HTTPNotFound
from pyramid.url import route_url
import colander as co
import couchdb.http

from .utils import PaginationSchema
from .utils import paginate_query


series_collection = Service(name='series_collection', path='/series')
series = Service(name='series', path='/series/{series}')
series_books = Service(
    name='series_books',
    path='/series/{series}/books/{book}',
)


@series_collection.get(schema=PaginationSchema)
def get_series_collection(request):
    """ Get all series.

    .. code-block:: js

        {
            "series": [
                "id": "myseriesid",
                "name": "Berserk",
                "description": "Berserk is a series written by Kentaro Miura.",
                "genre": [
                    "action",
                    "dark fantasy",
                    "tragedy"
                ]
            ]
        }

    """
    query = '''function(doc) {
        if (doc.type == "series") {
            emit({
                id: doc._id,
                name: doc.name,
                description: doc.description,
                genres: doc.genres
            })
        }
    }
    '''
    return paginate_query(request, query, 'series')


class PostSeriesCollectionSchema(co.MappingSchema):
    name = co.SchemaNode(co.String())
    description = co.SchemaNode(co.String())

    @co.instantiate()
    class genres(co.SequenceSchema):
        genre = co.SchemaNode(co.String())


@series_collection.post(schema=PostSeriesCollectionSchema)
def create_series(request):
    """ Create a series.

    .. code-block:: js

        {
            "name": "Berserk",
            "description": "Berserk is a series written by Kentaro Miura.",
            "genres": [
                "action",
                "dark fantasy",
                "tragedy"
            ]
        }

    """
    db = request.registry['godhand:db']
    _id, _rev = db.save({
        'type': 'series',
        'name': request.validated['name'],
        'description': request.validated['description'],
        'genres': request.validated['genres'],
        'books': [],
    })
    return {
        "series": [_id],
    }


class GetSeriesSchema(co.MappingSchema):
    series = co.SchemaNode(co.String(), location='path')


@series.get(schema=GetSeriesSchema)
def get_series(request):
    """ Get a series by key.

    .. code-block:: js

        {
            "id": "myid",
            "name": "Berserk",
            "description": "My description",
            "genres": [
                "action",
                "dark fantasy",
                "tragedy"
            ],
            "books": []
        }

    """
    db = request.registry['godhand:db']
    series_id = request.validated['series']
    try:
        doc = db[series_id]
    except couchdb.http.ResourceNotFound:
        raise HTTPNotFound(series_id)
    else:
        return {
            'id': doc['_id'],
            'name': doc['name'],
            'description': doc['description'],
            'genres': doc['genres'],
            'books': [{
                'id': x,
                'url': route_url('book', request, book=x),
            } for x in doc['books']],
        }


class PutSeriesBooks(co.MappingSchema):
    series = co.SchemaNode(co.String(), location='path')
    book = co.SchemaNode(co.String(), location='path')


@series_books.put(schema=PutSeriesBooks)
def add_book_to_series(request):
    db = request.registry['godhand:db']
    v = request.validated
    try:
        series = db[v['series']]
    except couchdb.http.ResourceNotFound:
        raise HTTPNotFound(v['series'])
    try:
        book = db[v['book']]
    except couchdb.http.ResourceNotFound:
        raise HTTPBadRequest
    series['books'].append(book.id)
    db[v['series']] = series
