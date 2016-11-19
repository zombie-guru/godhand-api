from pyramid.httpexceptions import HTTPNotFound
import colander as co

from ..models.series import SeriesReaderProgress
from ..models.series import Series
from ..models.volume import Volume
from .utils import GodhandService
from .utils import ValidatedVolume
from .utils import language_validator


class VolumePathSchema(co.MappingSchema):
    volume = co.SchemaNode(
        ValidatedVolume(), location='path', validator=co.NoneOf([None]))


class VolumePagePathSchema(VolumePathSchema):
    page = co.SchemaNode(co.Integer(), location='path')


volumes = GodhandService(
    name='volumes',
    path='/volumes',
)
volume = GodhandService(
    name='volume',
    path='/volumes/{volume}',
    schema=VolumePathSchema,
)
volume_cover = GodhandService(
    name='volume_cover',
    path='/volumes/{volume}/cover.jpg',
    permission='view'
)
volume_page = GodhandService(
    name='volume_page',
    path='/volumes/{volume}/pages/{page}'
)
volume_file = GodhandService(
    name='volume_file',
    path='/volumes/{volume}/files/{filename:.+}'
)
volume_reader_progress = GodhandService(
    name='volume_reader_progress',
    path='/volumes/{volume}/reader_progress'
)
reprocess_images = GodhandService(
    name='reprocess_images',
    path='/reprocess_images',
    permission='admin'
)


@volume.get(
    permission='view',
)
def get_volume(request):
    """ Get a volume by ID.

    .. code-block:: js

        {
            "id": "myuniqueid",
            "volume_number": 0,
            "pages": [
                {"url": "http://url.to.page0.jpg"}
            ]
        }

    """
    volume = request.validated['volume'].as_dict()
    for page in volume['pages']:
        page['url'] = request.route_url(
            'volume_file', volume=volume['id'], filename=page['filename'])

    next_volume = request.validated['volume'].get_next_volume(
        request.registry['godhand:db'])
    volume['next'] = None
    if next_volume:
        volume['next'] = next_volume.as_dict(short=True)
    return volume


class PutVolumeSchema(VolumePathSchema):
    series_id = co.SchemaNode(co.String(), missing=None)
    volume_number = co.SchemaNode(
        co.Integer(), validator=co.Range(min=0), missing=None)
    language = co.SchemaNode(
        co.String(), missing=None, validator=language_validator)


@volume.put(
    schema=PutVolumeSchema,
    permission='view',
)
def update_volume_meta(request):
    """ Update volume metadata.
    """
    keys = ('language', 'volume_number')
    db = request.registry['godhand:db']
    volume = request.validated['volume']
    series_id = request.validated['series_id']
    series = None
    if series_id:
        series = Series.load(db, series_id)
    volume.update_meta(
        db, series=series, **{k: request.validated[k] for k in keys})


@volume.delete(permission='write')
def delete_volume(request):
    request.validated['volume'].delete(request.registry['godhand:db'])


@volume_cover.get(schema=VolumePathSchema)
def get_volume_cover(request):
    """ Get a volume page.
    """
    volume = request.validated['volume']
    attachment = volume['_attachments']['cover.jpg']
    mimetype = attachment['content_type']
    attachment = request.registry['godhand:db'].get_attachment(
        volume.id, 'cover.jpg')
    if attachment is None:
        raise HTTPNotFound()
    response = request.response
    response.body_file = attachment
    response.content_type = mimetype
    return response


@volume_page.get(permission='view', schema=VolumePagePathSchema)
def get_volume_page(request):
    """ Get a volume page.
    """
    volume = request.validated['volume']
    try:
        page = volume.pages[request.validated['page']]
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


class VolumeFileSchema(VolumePathSchema):
    filename = co.SchemaNode(co.String(), location='path')


@volume_file.get(
    permission='view',
    schema=VolumeFileSchema,
)
def get_volume_file(request):
    attachment = request.registry['godhand:db'].get_attachment(
        request.validated['volume'].id,
        request.validated['filename'],
    )
    if attachment is None:
        raise HTTPNotFound()
    response = request.response
    response.body_file = attachment
    return response


@volume_file.delete(
    permission='write',
    schema=VolumeFileSchema,
)
def delete_volume_file(request):
    request.validated['volume'].delete_file(
        request.registry['godhand:db'], request.validated['filename'])


class StoreReaderProgressSchema(VolumePathSchema):
    page_number = co.SchemaNode(co.Integer(), validator=co.Range(min=0))


@volume_reader_progress.put(
    permission='view',
    schema=StoreReaderProgressSchema,
)
def store_reader_progress(request):
    v = request.validated
    SeriesReaderProgress.save_for_user(
        db=request.registry['godhand:db'],
        series_id=v['volume'].series_id,
        user_id=request.authenticated_userid,
        volume=v['volume'],
        page_number=v['page_number'],
    )


class ReprocessImagesSchema(co.MappingSchema):
    min_height = co.SchemaNode(co.Integer(), validator=co.Range(min=128))
    min_width = co.SchemaNode(co.Integer(), validator=co.Range(min=128))


@reprocess_images.post(schema=ReprocessImagesSchema)
def run_reprocess_images(request):
    Volume.reprocess_all_images(
        db=request.registry['godhand:db'],
        min_width=request.validated['min_width'],
        min_height=request.validated['min_height'],
    )
