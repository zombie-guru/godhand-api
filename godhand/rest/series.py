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
series_volume = Service(
    name='series_volume',
    path='/series/{series}/volumes/{volume}',
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
        'volumes': [],
    })
    return {
        'series': [_id],
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
            "volumes": []
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
            'volumes': [{
                'id': x,
                'url': route_url('volume', request, volume=x),
            } for x in doc['volumes']],
        }


class PutSeriesVolume(co.MappingSchema):
    series = co.SchemaNode(co.String(), location='path')
    volume = co.SchemaNode(co.String(), location='path')


@series_volume.put(schema=PutSeriesVolume)
def add_volume_to_series(request):
    db = request.registry['godhand:db']
    v = request.validated
    try:
        series = db[v['series']]
    except couchdb.http.ResourceNotFound:
        raise HTTPNotFound(v['series'])
    try:
        volume = db[v['volume']]
    except couchdb.http.ResourceNotFound:
        raise HTTPBadRequest
    series['volumes'].append(volume.id)
    db[v['series']] = series
