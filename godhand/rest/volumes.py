from pyramid.httpexceptions import HTTPNotFound
from pyramid.httpexceptions import HTTPForbidden
import colander as co

from ..models import Bookmark
from ..models import Series
from .utils import GodhandService
from .utils import ValidatedVolume
from .utils import language_validator


class VolumePathSchema(co.MappingSchema):
    volume = co.SchemaNode(
        ValidatedVolume(), location='path', validator=co.NoneOf([None]))


class VolumePagePathSchema(VolumePathSchema):
    page = co.SchemaNode(co.Integer(), location='path')


def check_can_view_volume(request):
    volume = request.validated['volume']
    if not volume.user_can_view(request.authenticated_userid):
        raise HTTPForbidden('User cannot view volume.')


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
)
volume_page = GodhandService(
    name='volume_page',
    path='/volumes/{volume}/pages/{page}'
)
volume_file = GodhandService(
    name='volume_file',
    path='/volumes/{volume}/files/{filename:.+}'
)
volume_bookmark = GodhandService(
    name='volume_bookmark',
    path='/volumes/{volume}/bookmark'
)


@volume.get()
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
    check_can_view_volume(request)
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


@volume.put(schema=PutVolumeSchema)
def update_volume_meta(request):
    """ Update volume metadata.
    """
    check_can_view_volume(request)  # TODO: check can write
    keys = ('language', 'volume_number')
    db = request.registry['godhand:db']
    volume = request.validated['volume']
    series_id = request.validated['series_id']
    series = None
    if series_id:
        series = Series.load(db, series_id)
    volume.update_meta(
        db, series=series, **{k: request.validated[k] for k in keys})


@volume.delete()
def delete_volume(request):
    check_can_view_volume(request)  # TODO: check can write
    request.validated['volume'].delete(request.registry['godhand:db'])


@volume_cover.get(schema=VolumePathSchema)
def get_volume_cover(request):
    """ Get a volume page.
    """
    check_can_view_volume(request)
    cover = request.validated['volume'].get_cover(
        request.registry['godhand:db'])
    if cover is None:
        raise HTTPNotFound()
    response = request.response
    response.body_file = cover
    response.content_type = 'image/jpeg'
    return response


@volume_page.get(schema=VolumePagePathSchema)
def get_volume_page(request):
    """ Get a volume page.
    """
    check_can_view_volume(request)
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


@volume_file.get(schema=VolumeFileSchema)
def get_volume_file(request):
    check_can_view_volume(request)
    attachment = request.registry['godhand:db'].get_attachment(
        request.validated['volume'].id,
        request.validated['filename'],
    )
    if attachment is None:
        raise HTTPNotFound()
    response = request.response
    response.body_file = attachment
    return response


@volume_file.delete(schema=VolumeFileSchema)
def delete_volume_file(request):
    check_can_view_volume(request)  # TODO: check can write
    request.validated['volume'].delete_file(
        request.registry['godhand:db'], request.validated['filename'])


class StoreReaderProgressSchema(VolumePathSchema):
    page_number = co.SchemaNode(co.Integer(), validator=co.Range(min=0))


@volume_bookmark.put(schema=StoreReaderProgressSchema)
def update_volume_bookmark(request):
    check_can_view_volume(request)
    Bookmark.update(
        db=request.registry['godhand:db'],
        user_id=request.authenticated_userid,
        volume=request.validated['volume'],
        page_number=request.validated['page_number'],
    )
