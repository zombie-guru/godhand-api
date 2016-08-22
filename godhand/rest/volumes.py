from pyramid.httpexceptions import HTTPNotFound
import colander as co

from ..models.volume import Volume
from .utils import GodhandService


class VolumePathSchema(co.MappingSchema):
    volume = co.SchemaNode(co.String(), location='path')


volumes = GodhandService(
    name='volumes',
    path='/volumes',
)
volume = GodhandService(
    name='volume',
    path='/volumes/{volume}',
    schema=VolumePathSchema,
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
    volume = Volume.load(
        request.registry['godhand:db'], request.validated['volume'])
    if volume is None:
        raise HTTPNotFound()
    for page in volume['pages']:
        page['url'] = request.static_url(page['path'])
    return dict(volume.items())


class PutVolumeSchema(VolumePathSchema):
    volume_number = co.SchemaNode(
        co.Integer(), validator=co.Range(min=0), missing=None)


@volume.put(
    schema=PutVolumeSchema,
    permission='view',
)
def update_volume_meta(request):
    """ Update volume metadata.
    """
    volume = Volume.load(
        request.registry['godhand:db'], request.validated['volume'])
    if volume is None:
        raise HTTPNotFound()
    for key in ('volume_number', 'language'):
        value = request.validated[key]
        if value:
            volume[key] = value
    volume.store(request.registry['godhand:db'])
