from cornice import Service
from pyramid.httpexceptions import HTTPNotFound
import colander as co
import couchdb.http

from ..models import Series
from ..models import Volume
from .utils import PaginationSchema
from .utils import paginate_query


series_collection = Service(name='series_collection', path='/series')
series = Service(name='series', path='/series/{series}')
series_volumes = Service(
    name='series_volumes', path='/series/{series}/volumes')


@series_collection.get(schema=PaginationSchema)
def get_series_collection(request):
    """ Get all series.
    """
    return paginate_query(request, Series.by_id, 'series')


class PostSeriesCollectionSchema(co.MappingSchema):
    name = co.SchemaNode(co.String(), missing=None)
    description = co.SchemaNode(co.String(), missing=None)
    author = co.SchemaNode(co.String(), missing=None)
    magazine = co.SchemaNode(co.String(), missing=None)
    number_of_volumes = co.SchemaNode(co.String(), missing=None)

    @co.instantiate(missing=())
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
    doc = Series(**request.validated)
    doc.store(request.registry['godhand:db'])
    return {
        'series': [doc.id],
    }


class SeriesPathSchema(co.MappingSchema):
    series = co.SchemaNode(co.String(), location='path')


@series.get(schema=SeriesPathSchema)
def get_series(request):
    """ Get a series by key.
    """
    db = request.registry['godhand:db']
    series_id = request.validated['series']
    try:
        doc = Series.load(db, series_id)
    except couchdb.http.ResourceNotFound:
        raise HTTPNotFound(series_id)
    else:
        if doc is None:
            raise HTTPNotFound(series_id)
        return dict(doc.items())


@series_volumes.post(
    schema=SeriesPathSchema, content_type=('multipart/form-data',))
def upload_volume(request):
    """ Create volume and return unique ids.
    """
    db = request.registry['godhand:db']
    series_id = request.validated['series']
    try:
        doc = Series.load(db, series_id)
    except couchdb.http.ResourceNotFound:
        raise HTTPNotFound(series_id)
    else:
        if doc is None:
            raise HTTPNotFound(series_id)
    volume_ids = []
    for key, value in request.POST.items():
        volume = Volume.from_archieve(
            books_path=request.registry['godhand:books_path'],
            filename=value.filename,
            fd=value.file,
        )
        volume.store(db)
        doc.add_volume(volume)
        volume_ids.append(volume.id)
    doc.store(db)
    return {'volumes': volume_ids}
