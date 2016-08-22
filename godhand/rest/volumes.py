from pyramid.httpexceptions import HTTPNotFound
import colander as co
import couchdb.http

from .utils import GodhandService


class VolumePathSchema(co.MappingSchema):
    volume = co.SchemaNode(co.String(), location='path')


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
    volume_id = request.validated['volume']
    db = request.registry['godhand:db']
    try:
        doc = db[volume_id]
    except couchdb.http.ResourceNotFound:
        raise HTTPNotFound(volume_id)
    else:
        for page in doc['pages']:
            page['url'] = request.static_url(page['path'])
        return dict(doc.items())


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
    v = request.validated
    volume_id = v['volume']
    db = request.registry['godhand:db']
    try:
        doc = db[volume_id]
    except couchdb.http.ResourceNotFound:
        raise HTTPNotFound(volume_id)
    for key in ('volume_number',):
        try:
            doc[key] = v[key]
        except KeyError:
            pass
    db.save(doc)


@volume_page.get(
    permission='view',
    schema=VolumePagePathSchema,
)
def get_volume_page(request):
    """ Get a volume page.
    """
    volume_id = request.validated['volume']
    db = request.registry['godhand:db']
    try:
        doc = db[volume_id]
    except couchdb.http.ResourceNotFound:
        raise HTTPNotFound(volume_id)
    try:
        page = doc['pages'][request.validated['page']]
    except IndexError:
        raise HTTPNotFound('Page does not exist.')
    return {
        'url': request.static_url(page['path']),
        'orientation': page['orientation'],
        'width': page['width'],
        'height': page['height'],
    }
