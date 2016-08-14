from pyramid.httpexceptions import HTTPNotFound
import colander as co
import couchdb.http

from ..models import Series
from ..models import SeriesReaderProgress
from ..models import Volume
from .utils import GodhandService
from .utils import paginate_view


search = GodhandService(
    name='search', path='/search')
series_collection = GodhandService(
    name='series_collection', path='/series')
series = GodhandService(name='series', path='/series/{series}')
series_volumes = GodhandService(
    name='series_volumes', path='/series/{series}/volumes')
series_reader_progress = GodhandService(
    name='series_reader_progress', path='/series/{series}/reader-progress')


class SearchSeriesSchema(co.MappingSchema):
    query = co.SchemaNode(co.String(), location='querystring', missing=None)


@search.get(permission='view', schema=SearchSeriesSchema)
def search_series(request):
    v = request.validated
    kws = {'group': True}
    if v['query']:
        kws['startkey'] = [v['query']]
        kws['endkey'] = [v['query'] + u'\ufff0']
    return paginate_view(request, Series.search, **kws)


def get_doc_from_request(request):
    db = request.registry['godhand:db']
    v = request.validated
    try:
        doc = Series.load(db, v['series'])
    except couchdb.http.ResourceNotFound:
        raise HTTPNotFound(v['series'])
    else:
        if doc is None:
            raise HTTPNotFound(v['series'])
    return doc


@series_collection.get(permission='view')
def get_series_collection(request):
    return paginate_view(request, Series.by_name)


class PostSeriesCollectionSchema(co.MappingSchema):
    name = co.SchemaNode(co.String(), missing=None)
    description = co.SchemaNode(co.String(), missing=None)
    author = co.SchemaNode(co.String(), missing=None)
    magazine = co.SchemaNode(co.String(), missing=None)
    number_of_volumes = co.SchemaNode(co.String(), missing=None)

    @co.instantiate(missing=())
    class genres(co.SequenceSchema):
        genre = co.SchemaNode(co.String())


@series_collection.post(
    schema=PostSeriesCollectionSchema,
    permission='write',
)
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
    Series.by_name.sync(request.registry['godhand:db'])
    Series.search.sync(request.registry['godhand:db'])
    return {
        'series': [doc.id],
    }


class SeriesPathSchema(co.MappingSchema):
    series = co.SchemaNode(co.String(), location='path')


@series.get(schema=SeriesPathSchema, permission='view')
def get_series(request):
    """ Get a series by key.
    """
    doc = get_doc_from_request(request)
    return dict(doc.items())


@series_volumes.post(
    schema=SeriesPathSchema,
    content_type=('multipart/form-data',),
    permission='write',
)
def upload_volume(request):
    """ Create volume and return unique ids.
    """
    doc = get_doc_from_request(request)
    db = request.registry['godhand:db']
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
    Series.by_name.sync(request.registry['godhand:db'])
    Series.search.sync(request.registry['godhand:db'])
    return {'volumes': volume_ids}


class StoreReaderProgressSchema(SeriesPathSchema):
    volume_number = co.SchemaNode(co.Integer(), validator=co.Range(min=0))
    page_number = co.SchemaNode(co.Integer(), validator=co.Range(min=0))


@series_reader_progress.put(
    schema=StoreReaderProgressSchema,
    permission='view',
)
def store_reader_progress(request):
    get_doc_from_request(request)
    v = request.validated
    key = SeriesReaderProgress.create_key(
        request.authenticated_userid, v['series'])
    progress = SeriesReaderProgress(
        volume_number=v['volume_number'], page_number=v['page_number'], id=key)
    progress.store(request.registry['godhand:db'])


@series_reader_progress.get(
    schema=SeriesPathSchema,
    permission='view',
)
def get_reader_progress(request):
    get_doc_from_request(request)
    v = request.validated
    key = SeriesReaderProgress.create_key(
        request.authenticated_userid, v['series'])
    p = SeriesReaderProgress.load(request.registry['godhand:db'], key)
    if p:
        return dict(p.items())
    return {'volume_number': 0, 'page_number': 0}
