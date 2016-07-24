import urllib.parse

from cornice import Service
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.httpexceptions import HTTPNotFound
import colander as co
import couchdb.http

from ..opendata import NoResultsForUri
from ..opendata import load_manga_resource
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
    uri = co.SchemaNode(
        co.String(), validator=co.url,
        description='Create from RDF resource of rdf:type dbo:Manga.',
        missing=None)
    name = co.SchemaNode(co.String(), missing=None)
    description = co.SchemaNode(co.String(), missing=None)

    @co.instantiate(missing=None)
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
    v = request.validated
    if v['uri']:
        try:
            doc = load_manga_resource(v['uri'])
            keys = (
                'name', 'description', 'author', 'magazine',
                'number_of_volumes',
            )
            for key in keys:
                try:
                    doc[key] = doc[key][0]
                except IndexError:
                    doc[key] = None
            doc['genres'] = doc.pop('genre')
        except NoResultsForUri:
            raise HTTPBadRequest('No results found for URI: {}'.format(
                v['uri']))
    else:
        doc = {
            'name': v['name'],
            'description': v['description'],
            'genres': v['genres'] if v['genres'] else list(),
        }
    doc['type'] = 'series'
    doc['volumes'] = []
    db = request.registry['godhand:db']
    _id, _rev = db.save(doc)
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
            'volumes': list(filter(
                lambda x: x is not None,
                (render_volume(request, x) for x in doc['volumes'])
            )),
        }


def render_volume(request, volume_id):
    db = request.registry['godhand:db']
    try:
        doc = db[volume_id]
    except couchdb.http.ResourceNotFound:
        return None
    if doc['type'] != 'volume':
        return None
    return {
        'id': doc['_id'],
        'volume_number': doc['volume_number'],
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
