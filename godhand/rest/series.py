from pyramid.exceptions import HTTPBadRequest
from pyramid.exceptions import HTTPForbidden
from pyramid.exceptions import HTTPNotFound
import colander as co

from ..models import Bookmark
from ..models import Series
from ..models import Volume
from .utils import GodhandService
from .utils import ValidatedSeries


class SeriesPathSchema(co.MappingSchema):
    series = co.SchemaNode(
        ValidatedSeries(), location='path', validator=co.NoneOf([None]),)


class UserPathSchema(co.MappingSchema):
    user = co.SchemaNode(co.String(), location='path', validator=co.Email())


series_collection = GodhandService(
    name='series_collection',
    path='/series',
)
series = GodhandService(
    name='series',
    path='/series/{series}',
    schema=SeriesPathSchema,
)
series_cover = GodhandService(
    name='series_cover',
    path='/series/{series}/cover.jpg',
    schema=SeriesPathSchema,
)
series_volumes = GodhandService(
    name='series_volumes',
    path='/series/{series}/volumes',
    schema=SeriesPathSchema,
)
user_series_collection = GodhandService(
    name='user_series_collection',
    path='/users/{user}/series',
    schema=UserPathSchema,
)


class GetSeriesCollectionSchema(co.MappingSchema):
    name_q = co.SchemaNode(co.String(), location='querystring', missing=None)


@series_collection.get(schema=GetSeriesCollectionSchema)
def get_series_collection(request):
    rows = Series.query(request.registry['godhand:db'], **request.validated)
    return {'items': [x.as_dict() for x in rows]}


class PostSeriesCollectionSchema(co.MappingSchema):
    name = co.SchemaNode(co.String(), missing=None)
    description = co.SchemaNode(co.String(), missing=None)
    author = co.SchemaNode(co.String(), missing=None)
    magazine = co.SchemaNode(co.String(), missing=None)
    number_of_volumes = co.SchemaNode(co.Integer(), missing=None)

    @co.instantiate(missing=())
    class genres(co.SequenceSchema):
        genre = co.SchemaNode(co.String())


@series_collection.post(schema=PostSeriesCollectionSchema)
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
    return doc.as_dict()


@series.get()
def get_series(request):
    """ Retrieve detailed info about a single series.

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
            ],
            "volumes": [
                {
                    "id": "abcdefg",
                    "filename": "volume-007.cbt",
                    "volume_number": 7,
                    "language": "en",
                    "number_of_pages": 147
                }
            ]
        }
    """
    series = request.validated['series']

    if not series.user_can_view(request.authenticated_userid):
        raise HTTPForbidden('User not allowed access to collection.')

    volumes = Volume.query(request.registry['godhand:db'], series_id=series.id)
    bookmarks = Bookmark.query(
        request.registry['godhand:db'],
        request.authenticated_userid,
        series_id=series.id)
    return dict(
        series.as_dict(),
        volumes=[x.as_dict(short=True) for x in volumes],
        bookmarks=[x.as_dict() for x in bookmarks]
    )


@series_cover.get()
def get_series_cover(request):
    series = request.validated['series']

    if not series.user_can_view(request.authenticated_userid):
        raise HTTPForbidden('User not allowed access to collection.')

    cover = series.get_cover(request.registry['godhand:db'])
    if cover is None:
        raise HTTPNotFound()
    response = request.response
    response.body_file = cover
    response.content_type = 'images/jpeg'
    return response


@series_volumes.post(content_type='multipart/form-data')
def upload_volume_to_series(request):
    """ Upload a volume to a series.
    """
    series = request.validated['series']
    try:
        volume_file = request.POST['volume']
    except KeyError:
        raise HTTPBadRequest('body volume is required')

    volume = Volume.from_archieve(
        request.registry['godhand:db'],
        owner_id=request.authenticated_userid,
        filename=volume_file.filename,
        fd=volume_file.file,
    )

    series.add_volume(
        request.registry['godhand:db'],
        owner_id=request.authenticated_userid,
        volume=volume,
    )
    return volume.as_dict()


@user_series_collection.get()
def get_user_series_collection(request):
    """ Get series uploaded by user.
    """
    if request.validated['user'] != request.authenticated_userid:
        # TODO: support subscribers
        raise HTTPForbidden('User not allowed access to collection.')

    rows = Series.query(
        request.registry['godhand:db'],
        owner_id=request.validated['user'],
    )
    return {'items': [x.as_dict() for x in rows]}
