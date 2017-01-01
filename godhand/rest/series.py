from pyramid.exceptions import HTTPBadRequest
from pyramid.exceptions import HTTPForbidden
from pyramid.exceptions import HTTPNotFound
import colander as co

from ..models import Bookmark
from ..models import Series
from ..models import Volume
from .utils import GodhandService
from .utils import ValidatedSeries
from .utils import owner_group
from .utils import subscription_group


class SeriesPathSchema(co.MappingSchema):
    series = co.SchemaNode(
        ValidatedSeries(), location="path", validator=co.NoneOf([None]),)


class UserPathSchema(co.MappingSchema):
    user = co.SchemaNode(co.String(), location="path", validator=co.Email())


def check_can_view_user_series(request, owner_id):
    ok_groups = [
        subscription_group(owner_id),
        owner_group(owner_id),
    ]
    if not any(x in request.effective_principals for x in ok_groups):
        raise HTTPForbidden('User cannot view series.')


def check_can_view_series(request, ignore_root=False):
    series = request.validated['series']
    if ignore_root and series.owner_id == 'root':
        # everyone can read root
        return
    ok_groups = [
        subscription_group(series.owner_id),
        owner_group(series.owner_id),
    ]
    if not any(x in request.effective_principals for x in ok_groups):
        raise HTTPForbidden('User cannot view series.')


def check_can_write_series(request, ignore_root=False):
    series = request.validated['series']
    if ignore_root and series.owner_id == 'root':
        # everyone can "write" to root - a copy of the series will be made.
        return
    ok_groups = [
        owner_group(series.owner_id),
    ]
    if not any(x in request.effective_principals for x in ok_groups):
        raise HTTPForbidden('User cannot write series.')


series_collection = GodhandService(
    name="series collection",
    path="/series",
)
series = GodhandService(
    name="series",
    path="/series/{series}",
    schema=SeriesPathSchema,
)
series_cover = GodhandService(
    name="series cover",
    path="/series/{series}/cover.jpg",
    schema=SeriesPathSchema,
)
series_volumes = GodhandService(
    name="series volumes",
    path="/series/{series}/volumes",
    schema=SeriesPathSchema,
)
user_series_collection = GodhandService(
    name="user series collection",
    path="/users/{user}/series",
    schema=UserPathSchema,
)


class GetSeriesCollectionSchema(co.MappingSchema):
    name_q = co.SchemaNode(co.String(), location="querystring", missing=None)


@series_collection.get(schema=GetSeriesCollectionSchema)
def get_series_collection(request):
    """ Get read-only series information.

    .. code-block:: js

        {"items": [{
            "id": "dbr:Berserk",
            "name": "Berserk",
            "description": "my description",
            "genres": ["action"],
            "author": "Kentaro Miura",
            "magazine": "Young Animal",
            "number_of_volumes": 14
        }]}

    """
    rows = Series.query(request.registry["godhand:db"], **request.validated)
    return {"items": [x.as_dict() for x in rows]}


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
    """
    doc = Series.create(request.registry["godhand:db"], **request.validated)
    return doc.as_dict()


@series.get()
def get_series(request):
    """ Retrieve detailed info about a single series.

    .. code-block:: js

        {
            "id": "dbr:Berserk",
            "name": "Berserk",
            "description": "Berserk is a series written by Kentaro Miura.",
            "genres": ["action"],
            "author": "Kentaro Miura",
            "magazine": "Young Animal",
            "number_of_volumes": 14,
            "volumes": [{
                "id": "volume001",
                "filename": "volume001.tgz",
                "volume_number": 1,
                "language": "jpn",
                "pages": 127
            }],
            "bookmarks": [{
                "series_id": "dbr:Berserk"
                "volume_id": "volume001",
                "number_of_pages": 127,
                "page_number": 4,
                "last_updated": "2014-04-08T 4:07:07.748",
                "volume_number": 1,
                "page0": "http://page0.jpg",
                "page1": "http://page1.jpg"
            }]
        }

    """
    check_can_view_series(request, ignore_root=True)

    series = request.validated["series"]
    volumes = Volume.query(request.registry["godhand:db"], series_id=series.id)
    bookmarks = Bookmark.query(
        request.registry["godhand:db"],
        request.authenticated_userid,
        series_id=series.id)
    return dict(
        series.as_dict(),
        volumes=[x.as_dict(short=True) for x in volumes],
        bookmarks=[x.as_dict(request) for x in bookmarks]
    )


@series_cover.get()
def get_series_cover(request):
    """ Get cover page as image.
    """
    check_can_view_series(request, ignore_root=True)
    series = request.validated["series"]

    cover = series.get_cover(request.registry["godhand:db"])
    if cover is None:
        raise HTTPNotFound()
    response = request.response
    response.body_file = cover
    response.content_type = "images/jpeg"
    return response


@series_volumes.post(content_type="multipart/form-data")
def upload_volume_to_series(request):
    """ Upload a volume to a series and return the new volume.

    If a series is read-only, a new one for the user will be created as a
    duplicate.

    """
    check_can_write_series(request, ignore_root=True)

    series = request.validated["series"]
    try:
        volume_file = request.POST["volume"]
    except KeyError:
        raise HTTPBadRequest("body volume is required")

    volume = Volume.from_archieve(
        request.registry["godhand:db"],
        owner_id=request.authenticated_userid,
        filename=volume_file.filename,
        fd=volume_file.file,
    )

    series.add_volume(
        request.registry["godhand:db"],
        owner_id=request.authenticated_userid,
        volume=volume,
    )
    return volume.as_dict()


@user_series_collection.get()
def get_user_series_collection(request):
    """ Get series uploaded by user.

    .. code-block:: js

        {"items": [{
            "id": "dbr:Berserk",
            "name": "Berserk",
            "description": "my description",
            "genres": ["action"],
            "author": "Kentaro Miura",
            "magazine": "Young Animal",
            "number_of_volumes": 14
        }]}

    """
    check_can_view_user_series(request, request.validated['user'])

    rows = Series.query(
        request.registry["godhand:db"],
        owner_id=request.validated["user"],
    )
    return {"items": [x.as_dict() for x in rows]}
