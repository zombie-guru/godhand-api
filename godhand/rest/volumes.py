import locale

from pyramid.httpexceptions import HTTPNotFound
import colander as co

from ..models.series import SeriesReaderProgress
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
        co.Integer(), validator=co.Range(min=0), missing=co.drop)
    language = co.SchemaNode(
        co.String(), missing=co.drop,
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
        volume[key] = value
    volume.store(request.registry['godhand:db'])


@volume_page.get(
    permission='view',
    schema=VolumePagePathSchema,
)
def get_volume_page(request):
    """ Get a volume page.
    """
    volume = request.validated['volume']
    try:
        page = volume.pages[request.validated['page']]
    except IndexError:
        raise HTTPNotFound('Page does not exist.')
    return {
        'url': request.route_url(
            'volume_file',
            volume=volume.id,
            filename=page['filename'],
        ),
        'orientation': page['orientation'],
        'width': page['width'],
        'height': page['height'],
    }


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
