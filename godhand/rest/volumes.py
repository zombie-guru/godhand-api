import os
import re
import tempfile

from cornice import Service
from pyramid.httpexceptions import HTTPNotFound
import colander as co
import couchdb.http

from godhand import bookextractor
from .utils import PaginationSchema
from .utils import paginate_query


class VolumePathSchema(co.MappingSchema):
    volume = co.SchemaNode(co.String(), location='path')


volumes = Service(
    name='volumes',
    path='/volumes',
)
volume = Service(
    name='volume',
    path='/volumes/{volume}',
    schema=VolumePathSchema,
)


@volumes.get(schema=PaginationSchema)
def get_volumes(request):
    """ Get all volumes.

    .. code-block:: js

        {
            "volumes": [
                {
                    "id": "myid",
                    "volume_number": 0,
                }
            ],
            "offset": 0,
            "total": 1
        }

    """
    query = '''function(doc) {
        if (doc.type == "volume") {
            emit({
                id: doc._id,
                volume_number: doc.volume_number
            })
        }
    }
    '''
    obj = paginate_query(request, query, 'volumes')
    return obj


@volumes.post(content_type=('multipart/form-data',))
def upload_volume(request):
    """ Create volume and return unique ids.
    """
    volume_ids = []
    for key, value in request.POST.items():
        basedir = tempfile.mkdtemp(dir=request.registry['godhand:books_path'])
        extractor_cls = bookextractor.from_filename(value.filename)
        extractor = extractor_cls(value.file, basedir)
        # try to infer volume number
        try:
            volume_number = int(re.findall('\d+', value.filename)[-1])
        except IndexError:
            volume_number = None
        volume = {
            'type': 'volume',
            'volume_number': volume_number,
            'path': basedir,
            'pages': [{
                'path': page,
            } for page, mimetype in extractor.iter_pages()]
        }
        _id, _rev = request.registry['godhand:db'].save(volume)
        volume_ids.append(_id)
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
        return {
            'id': doc['_id'],
            'volume_number': doc['volume_number'],
            'pages': [{
                'url': request.static_url(
                    os.path.join(doc['path'], x['path'])),
            } for x in doc['pages']]
        }


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
