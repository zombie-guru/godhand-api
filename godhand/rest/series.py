from cornice import Service
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.httpexceptions import HTTPNotFound
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


class GetSeriesCollectionSchema(PaginationSchema):
    only_has_volumes = co.SchemaNode(
        co.Boolean(), missing=True, location='querystring',
        description='Only include series with associated volumes.')
    name_q = co.SchemaNode(
        co.String(), missing=None, location='querystring',
        description='Query name field of series.')


@series_collection.get(schema=GetSeriesCollectionSchema)
def get_series_collection(request):
    """ Get all series.

    .. code-block:: js

        {
            "series": [
                "id": "myseriesid",
                "name": "Berserk",
                "description": "Berserk is a series written by Kentaro Miura.",
                "dbpedia_uri": "http://dbpedia.org/resource/Berserk_(manga)",
                "author": "Kentaro Miura",
                "magazine": "Young Animal",
                "number_of_volumes": 38,
                "genre": [
                    "action",
                    "dark fantasy",
                    "tragedy"
                ]
            ]
        }

    """
    only_has_volumes = ''
    if request.validated['only_has_volumes']:
        only_has_volumes = '&& (doc.volumes.length > 0)'
    name_q = ''
    if request.validated['name_q']:
        name_q = '&& (/%s/i.test(doc.name))' % request.validated['name_q']
    query = '''function(doc) {
        if ( (doc.type == "series") %(only_has_volumes)s %(name_q)s) {
            emit({
                id: doc._id,
                name: doc.name,
                description: doc.description,
                genres: doc.genres,
                dbpedia_uri: doc.dbpedia_uri,
                author: doc.author,
                magazine: doc.magazine,
                number_of_volumes: doc.number_of_volumes
            })
        }
    }
    ''' % {'only_has_volumes': only_has_volumes, 'name_q': name_q}
    return paginate_query(request, query, 'series')


class PostSeriesCollectionSchema(co.MappingSchema):
    name = co.SchemaNode(co.String(), missing=None)
    description = co.SchemaNode(co.String(), missing=None)
    author = co.SchemaNode(co.String(), missing=None)
    magazine = co.SchemaNode(co.String(), missing=None)
    number_of_volumes = co.SchemaNode(co.String(), missing=None)

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
            "dbpedia_uri": "http://dbpedia.org/resource/Berserk_(manga)",
            "author": "Kentaro Miura",
            "magazine": "Young Animal",
            "number_of_volumes": 38,
            "genres": [
                "action",
                "dark fantasy",
                "tragedy"
            ]
        }

    """
    v = request.validated
    doc = {
        'name': v['name'],
        'description': v['description'],
        'genres': v['genres'] if v['genres'] else list(),
        'author': v['author'],
        'magazine': v['magazine'],
        'number_of_volumes': v['number_of_volumes'],
        'dbpedia_uri': None,
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
            "dbpedia_uri": "http://dbpedia.org/resource/Berserk_(manga)",
            "author": "Kentaro Miura",
            "magazine": "Young Animal",
            "number_of_volumes": 38,
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
            'dbpedia_uri': doc['dbpedia_uri'],
            'author': doc.get('author'),
            'magazine': doc.get('magazine'),
            'number_of_volumes': doc.get('number_of_volumes'),
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
    """ Add a volume to a series.
    """
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
