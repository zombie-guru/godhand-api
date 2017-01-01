from pyramid.httpexceptions import HTTPNotFound
from pyramid.httpexceptions import HTTPForbidden
import colander as co

from ..models import Bookmark
from .utils import GodhandService
from .utils import ValidatedVolume
from .utils import language_validator
from .utils import owner_group
from .utils import subscription_group


class VolumePathSchema(co.MappingSchema):
    volume = co.SchemaNode(
        ValidatedVolume(), location='path', validator=co.NoneOf([None]))


class VolumePagePathSchema(VolumePathSchema):
    page = co.SchemaNode(co.Integer(), location='path')


def check_can_view_volume(request):
    volume = request.validated['volume']
    ok_groups = [
        subscription_group(volume.owner_id),
        owner_group(volume.owner_id),
    ]
    if not any(x in request.effective_principals for x in ok_groups):
        raise HTTPForbidden('User cannot view volume.')


def check_can_write_volume(request):
    volume = request.validated['volume']
    ok_groups = [
        owner_group(volume.owner_id),
    ]
    if not any(x in request.effective_principals for x in ok_groups):
        raise HTTPForbidden('User cannot view volume.')


volume = GodhandService(
    name='volume',
    path='/volumes/{volume}',
    schema=VolumePathSchema,
)
volume_cover = GodhandService(
    name='volume cover',
    path='/volumes/{volume}/cover.jpg',
)
volume_file = GodhandService(
    name='volume file',
    path='/volumes/{volume}/files/{filename:.+}'
)
volume_bookmark = GodhandService(
    name='volume bookmark',
    path='/volumes/{volume}/bookmark'
)


@volume.get()
def get_volume(request):
    """ Get a volume by ID.

    .. code-block:: js

        {
            "id": "myuniqueid",
            "volume_number": 0,
            "pages": [{
                "url": "http://url.to.page0.jpg"
                "filename": "page0.jpg",
                "width": 400,
                "height": 800,
                "orientation": "vertical"
            }]
        }

    """
    check_can_view_volume(request)
    volume = request.validated['volume'].as_dict()
    for page in volume['pages']:
        page['url'] = request.route_url(
            'volume file', volume=volume['id'], filename=page['filename'])

    next_volume = request.validated['volume'].get_next_volume(
        request.registry['godhand:db'])
    volume['next'] = None
    if next_volume:
        volume['next'] = next_volume.as_dict(short=True)
    return volume


class PutVolumeSchema(VolumePathSchema):
    volume_number = co.SchemaNode(
        co.Integer(), validator=co.Range(min=0), missing=None)
    language = co.SchemaNode(
        co.String(), missing=None, validator=language_validator)


@volume.put(schema=PutVolumeSchema)
def update_volume_meta(request):
    """ Update volume metadata.
    """
    check_can_write_volume(request)
    keys = ('language', 'volume_number')
    db = request.registry['godhand:db']
    volume = request.validated['volume']
    volume.update_meta(db, **{k: request.validated[k] for k in keys})


@volume.delete()
def delete_volume(request):
    """ Delete volume.
    """
    check_can_write_volume(request)
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


class VolumeFileSchema(VolumePathSchema):
    filename = co.SchemaNode(co.String(), location='path')


@volume_file.get(schema=VolumeFileSchema)
def get_volume_file(request):
    """ Get volume file bytes.
    """
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
    """ Delete file of volume.
    """
    check_can_write_volume(request)
    request.validated['volume'].delete_file(
        request.registry['godhand:db'], request.validated['filename'])


class StoreReaderProgressSchema(VolumePathSchema):
    page_number = co.SchemaNode(co.Integer(), validator=co.Range(min=0))


@volume_bookmark.put(schema=StoreReaderProgressSchema)
def update_volume_bookmark(request):
    """ Update bookmark for volume.
    """
    check_can_view_volume(request)
    Bookmark.update(
        db=request.registry['godhand:db'],
        user_id=request.authenticated_userid,
        volume=request.validated['volume'],
        page_number=request.validated['page_number'],
    )
