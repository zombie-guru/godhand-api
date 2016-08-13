from pyramid.httpexceptions import HTTPNotFound
import colander as co
import couchdb.http

from ..models import Volume
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


@volumes.post(content_type=('multipart/form-data',))
def upload_volume(request):
    """ Create volume and return unique ids.
    """
    volume_ids = []
    for key, value in request.POST.items():
        volume = Volume.from_archieve(
            books_path=request.registry['godhand:books_path'],
            filename=value.filename,
            fd=value.file,
        )
        res = volume.store(request.registry['godhand:db'])
        volume_ids.append(res.id)
    return {'volumes': volume_ids}


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


@volume.put(schema=PutVolumeSchema)
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
