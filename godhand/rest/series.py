from pyramid.httpexceptions import HTTPBadRequest
from pyramid.httpexceptions import HTTPNotFound
import colander as co

from ..models import Series
from ..models import SeriesReaderProgress
from ..models import Volume
from .utils import GodhandService
from .utils import ValidatedSeries


class SeriesPathSchema(co.MappingSchema):
    series = co.SchemaNode(
        ValidatedSeries(), location='path', validator=co.NoneOf([None]),)


class SeriesVolumePathSchema(SeriesPathSchema):
    n_volume = co.SchemaNode(co.Integer(), location='path')


class SeriesVolumePagePathSchema(SeriesVolumePathSchema):
    n_page = co.SchemaNode(co.Integer(), location='path')


series_collection = GodhandService(
    name='series_collection', path='/series')
series = GodhandService(name='series', path='/series/{series}')
series_cover_page = GodhandService(
    name='series_cover_page', path='/series/{series}/cover_page')
series_volumes = GodhandService(
    name='series_volumes', path='/series/{series}/volumes')
series_volume = GodhandService(
    name='series_volume', path='/series/{series}/volumes/{n_volume}')
series_volume_page = GodhandService(
    name='series_volume_page',
    path='/series/{series}/volumes/{n_volume}/pages/{n_page}')
series_reader_progress = GodhandService(
    name='series_reader_progress', path='/series/{series}/reader_progress')


class GetSeriesCollectionSchema(co.MappingSchema):
    genre = co.SchemaNode(co.String(), location='querystring', missing=None)
    name = co.SchemaNode(co.String(), location='querystring', missing=None)
    include_empty = co.SchemaNode(
        co.Boolean(), location='querystring', missing=False)
    full_match = co.SchemaNode(
        co.Boolean(), location='querystring', missing=False,
        description='Only return full matches.')


@series_collection.get(permission='view', schema=GetSeriesCollectionSchema)
def get_series_collection(request):
    db = request.registry['godhand:db']
    try:
        view = Series.query(db, **request.validated)
    except ValueError as e:
        raise HTTPBadRequest(repr(e))
    return {'items': [dict(x.items()) for x in iter(view)]}


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
    doc = Series.create(request.registry['godhand:db'], **request.validated)
    return {
        'series': [doc.id],
    }


@series.get(schema=SeriesPathSchema, permission='view')
def get_series(request):
    """ Get a series by key.
    """
    series = request.validated['series']
    volumes = series.get_volumes_and_progress(
        request.registry['godhand:db'],
        request.authenticated_userid)
    return dict(series.items(), volumes=volumes)


@series_volumes.post(
    schema=SeriesPathSchema,
    content_type=('multipart/form-data',),
    permission='write',
)
def upload_volume(request):
    """ Create volume and return unique ids.
    """
    doc = request.validated['series']
    db = request.registry['godhand:db']
    volume_ids = []
    for key, value in request.POST.items():
        volume = Volume.from_archieve(
            db,
            filename=value.filename,
            fd=value.file,
            series_id=doc.id,
        )
        doc.uploaded_volumes += 1
        volume_ids.append(volume.id)
    doc.store(db)
    Series.by_attribute.sync(request.registry['godhand:db'])
    return {'volumes': volume_ids}


@series_volumes.get(
    schema=SeriesPathSchema,
    permission='view',
)
def get_series_volumes(request):
    series = request.validated['series']
    return {
        'volumes': series.get_volumes_and_progress(
            request.registry['godhand:db'],
            request.authenticated_userid,
        )
    }


@series_volume.get(
    schema=SeriesVolumePathSchema,
    permission='view',
)
def get_series_volume(request):
    """ Get a series volume by index.
    """
    v = request.validated
    try:
        volume = Volume.get_series_volume(
            request.registry['godhand:db'], v['series'].id, v['n_volume'])
    except IndexError:
        raise HTTPNotFound()
    result = dict(volume.items())
    for page in result['pages']:
        page['url'] = request.route_url(
            'volume_file', volume=volume.id, filename=page['filename'])
    return result


@series_volume_page.get(
    schema=SeriesVolumePagePathSchema,
    permission='view',
)
def get_series_volume_page(request):
    """ Get a volume page by offset.
    """
    v = request.validated
    try:
        volume = Volume.get_series_volume(
            request.registry['godhand:db'], v['series'].id, v['n_volume'])
    except IndexError:
        raise HTTPNotFound()

    try:
        page = volume.pages[request.validated['n_page']]
    except IndexError:
        raise HTTPNotFound('Page does not exist.')

    attachment = volume['_attachments'][page['filename']]
    mimetype = attachment['content_type']

    attachment = request.registry['godhand:db'].get_attachment(
        volume.id, page['filename'])
    if attachment is None:
        raise HTTPNotFound()
    response = request.response
    response.body_file = attachment
    response.content_type = mimetype
    return response


class SetSeriesCoverPageSchema(SeriesPathSchema):
    volume_id = co.SchemaNode(co.String(), location='body')
    page_number = co.SchemaNode(
        co.Integer(), location='body', validator=co.Range(min=0))


@series_cover_page.put(
    schema=SetSeriesCoverPageSchema,
    permission='write',
)
def set_series_cover_page(request):
    db = request.registry['godhand:db']
    v = request.validated
    series = v['series']
    volume = Volume.load(db, v['volume_id'])
    if volume is None:
        raise HTTPBadRequest('Invalid volume.')
    try:
        volume.pages[v['page_number']]
    except IndexError:
        raise HTTPBadRequest('Invalid page number')
    series.cover_page = {
        'volume_id': volume.id,
        'page_number': v['page_number'],
    }
    series.store(db)


@series_reader_progress.get(
    schema=SeriesPathSchema,
    permission='view',
)
def get_reader_progress(request):
    items = SeriesReaderProgress.retrieve_for_user(
        db=request.registry['godhand:db'],
        user_id=request.authenticated_userid,
        series_id=request.validated['series'].id,
    )
    return {'items': [dict(x.items()) for x in items]}
