import locale

from pyramid.httpexceptions import HTTPNotFound
import colander as co

from ..models.series import SeriesReaderProgress
from ..models.volume import Volume
from .utils import GodhandService
from .utils import ValidatedVolume


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
volume_next = GodhandService(
    name='volume_next',
    path='/volumes/{volume}/next'
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
    volume = request.validated['volume']
    for page in volume['pages']:
        page['url'] = request.route_url(
            'volume_file', volume=volume.id, filename=page['filename'])
    return dict(volume.items())


class PutVolumeSchema(VolumePathSchema):
    volume_number = co.SchemaNode(
        co.Integer(), validator=co.Range(min=0), missing=None)
    language = co.SchemaNode(
        co.String(), missing=None,
        validator=co.OneOf(set(locale.locale_alias.keys()))
    )


@volume.put(
    schema=PutVolumeSchema,
    permission='view',
)
def update_volume_meta(request):
    """ Update volume metadata.
    """
    volume = request.validated['volume']
    for key in ('volume_number', 'language'):
        try:
            value = request.validated[key]
        except KeyError:
            continue
        if value:
            volume[key] = value
    volume.store(request.registry['godhand:db'])


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


@volume_next.get(
    permission='view',
    schema=VolumePathSchema
)
def get_next_volume(request):
    next_volume = request.validated['volume'].get_next_volume(
        request.registry['godhand:db'])
    if next_volume:
        return dict(next_volume.items())
    return None


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
        volume_id=v['volume'].id,
        page_number=v['page_number'],
    )


class ReprocessImagesSchema(co.MappingSchema):
    width = co.SchemaNode(co.Integer(), validator=co.Range(min=128))
    blur_radius = co.SchemaNode(
        co.Integer(), validator=co.Range(min=0), missing=None)
    as_thumbnail = co.SchemaNode(
        co.Boolean(), missing=False)


@reprocess_images.post(schema=ReprocessImagesSchema)
def run_reprocess_images(request):
    Volume.reprocess_all_images(
        db=request.registry['godhand:db'],
        width=request.validated['width'],
        blur_radius=request.validated['blur_radius'],
        as_thumbnail=request.validated['as_thumbnail'],
    )
