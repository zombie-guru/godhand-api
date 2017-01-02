from functools import partial

from cornice import Service
from pyramid.exceptions import HTTPBadRequest
from pyramid.exceptions import HTTPNotFound
from pyramid.security import Allow
from pyramid.security import Authenticated
import colander as co
import pycountry

from .models import Bookmark
from .models import Series
from .models import Subscription
from .models import UserSettings
from .models import Volume
from .utils import owner_group
from .utils import subscription_group


def acl_by_owner(owner_id):
    return [
        (Allow, subscription_group(owner_id), 'read'),
        (Allow, owner_group(owner_id), 'read'),
        (Allow, owner_group(owner_id), 'write'),
    ]


def language_validator(node, cstruct):
    try:
        pycountry.languages.get(iso639_3_code=cstruct)
    except KeyError:
        raise co.Invalid(node, 'Invalid ISO639-3 code.')


class ValidatedSeries(co.String):
    def deserialize(self, node, cstruct):
        appstruct = super(ValidatedSeries, self).deserialize(node, cstruct)
        db = node.bindings['request'].registry['godhand:db']
        return Series.load(db, appstruct)


class ValidatedVolume(co.String):
    def deserialize(self, node, cstruct):
        appstruct = super(ValidatedVolume, self).deserialize(node, cstruct)
        db = node.bindings['request'].registry['godhand:db']
        return Volume.load(db, appstruct)


class UserPathSchema(co.MappingSchema):
    user = co.SchemaNode(co.String(), location="path", validator=co.Email())


class SeriesPathSchema(co.MappingSchema):
    series = co.SchemaNode(
        ValidatedSeries(), location="path", validator=co.NoneOf([None]),)


class VolumePathSchema(co.MappingSchema):
    volume = co.SchemaNode(
        ValidatedVolume(), location='path', validator=co.NoneOf([None]))


class VolumePagePathSchema(VolumePathSchema):
    page = co.SchemaNode(co.Integer(), location='path')


GodhandService = partial(
    Service,
    acl=lambda r: [(Allow, Authenticated, 'info')],
    permission='info',
)
account = GodhandService(
    name='account',
    path='/account',
    permission=None,
)
bookmarks = GodhandService(
    name='bookmarks',
    path='/bookmarks',
)
series_collection = GodhandService(
    name="series collection",
    path="/series",
)
subscribers = GodhandService(
    name='subscribers',
    description='Manage subscribers to our volumes.',
    path='/subscribers',
)
subscriptions = GodhandService(
    name='subscriptions',
    description='Manage subscriptions to other users\' volumes.',
    path='/subscriptions',
)


def series_acl(request):
    series_id = request.matchdict['series']
    series = Series.load(request.registry['godhand:db'], series_id)
    if series:
        if series.owner_id == 'root':
            return [
                (Allow, Authenticated, 'read'),
                (Allow, Authenticated, 'write'),
            ]
        return acl_by_owner(series.owner_id)
    raise HTTPNotFound('Series<{}>'.format(series_id))


SeriesService = partial(
    GodhandService,
    schema=SeriesPathSchema,
    acl=series_acl,
    permission='read',
)
series = SeriesService(
    name="series",
    path="/series/{series}",
)
series_cover = SeriesService(
    name="series cover",
    path="/series/{series}/cover.jpg",
)
series_volumes = SeriesService(
    name="series volumes",
    path="/series/{series}/volumes",
)


def user_acl(request):
    owner_id = request.matchdict['user']
    return acl_by_owner(owner_id)


UserService = partial(
    GodhandService,
    schema=UserPathSchema,
    acl=user_acl,
    permission='read'
)
user_series_collection = UserService(
    name="user series collection",
    path="/users/{user}/series",
)


def volume_acl(request):
    volume_id = request.matchdict['volume']
    volume = Volume.load(request.registry['godhand:db'], volume_id)
    if volume:
        return acl_by_owner(volume.owner_id)
    raise HTTPNotFound('Volume<{}>'.format(volume_id))


VolumeService = partial(
    GodhandService,
    schema=VolumePathSchema,
    acl=volume_acl,
    permission='read'
)
volume = VolumeService(
    name='volume',
    path='/volumes/{volume}',
)
volume_cover = VolumeService(
    name='volume cover',
    path='/volumes/{volume}/cover.jpg',
)
volume_file = VolumeService(
    name='volume file',
    path='/volumes/{volume}/files/{filename:.+}'
)
volume_bookmark = VolumeService(
    name='volume bookmark',
    path='/volumes/{volume}/bookmark',
)


@account.get()
def get_account_info(request):
    """ Get account information.

    .. code-block:: js

        {
            "needs_authentication": false,
            "subscriptions": [
                {"id": "cool.user@gmail.com"}
            ],
            "subscriber_requests": [
                {"id": "me.too@gmail.com"}
            ],
            "subscription_requests": [
                {"id": "i.have.good.stuff@gmail.com"}
            ],
            "id": "so.ronery@gmail.com",
            "usage": 1024
        }

    """
    if request.authenticated_userid is None:
        return {
            'needs_authentication': True,
        }
    return {
        'needs_authentication': False,
        'subscribed_ids': UserSettings.get_subscribed_owner_ids(
            request.registry['godhand:db'], request.authenticated_userid),
        'user_id': request.authenticated_userid,
        'usage': Volume.get_user_usage(
            request.registry['godhand:db'], request.authenticated_userid)
    }


@bookmarks.get()
def get_bookmarks(request):
    """ Get bookmarks for logged in user.

    .. code-block:: js

        {
            "series_id": "series-abc",
            "volume_id": "volume-abc",
            "number_of_pages": 18,
            "page_number": 0,
            "last_updated": "2016-01-04 14:16:39.000",
            "volume_number": 8,
            "page0": "http://left.png",
            "page1": null
        }

    """
    rows = Bookmark.query(
        request.registry['godhand:db'], user_id=request.authenticated_userid)
    return {'items': [x.as_dict(request) for x in rows]}


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
    series = request.validated["series"]
    cover = series.get_cover(request.registry["godhand:db"])
    if cover is None:
        raise HTTPNotFound()
    response = request.response
    response.body_file = cover
    response.content_type = "images/jpeg"
    return response


@series_volumes.post(content_type='multipart/form-data', permission='write')
def upload_volume_to_series(request):
    """ Upload a volume to a series and return the new volume.

    If a series is read-only, a new one for the user will be created as a
    duplicate.

    """
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
    rows = Series.query(
        request.registry["godhand:db"],
        owner_id=request.validated["user"],
    )
    return {"items": [x.as_dict() for x in rows]}


@subscribers.get()
def get_subscribers(request):
    """ Get users that have subscribed to our volumes.

    .. code-block:: js

        {"items": [
            {"id": "so.ronery@gmail.com"}
        ]}

    """
    rows = Subscription.query(
        request.registry['godhand:db'],
        publisher_id=request.authenticated_userid)
    return {'items': [x.as_dict() for x in rows]}


class PutSubscribersSchema(co.MappingSchema):
    action = co.SchemaNode(
        co.String(), validator=co.OneOf(['allow', 'block', 'clear']))
    user_id = co.SchemaNode(co.String(), validator=co.Email())


@subscribers.put(schema=PutSubscribersSchema)
def update_subscribers(request):
    """ Update subscriber status for a user.

    If ``allow`` is sent for ``so.ronery@gmail.com``, we are allowing that user
    to subscribe to our volumes and they will see us in
    ``subscriber_requests``. Note that they will need to use
    ``PUT /account/subscriptions`` as well to confirm this.

    Sending ``block`` will remove them from your ``subscription_requests``.

    Sending ``clear`` will remove your preference. If a subscriber is
    requested, it will show up again in your ``subscription_requests``.

    """
    db = request.registry['godhand:db']
    v = request.validated
    Subscription.retrieve(
        request.registry['godhand:db'],
        subscriber_id=v['user_id'],
        publisher_id=request.authenticated_userid
    ).update_publisher_status(db, v['action'])


@subscriptions.get()
def get_subscriptions(request):
    """ Get users that have we have subscribed to.

    .. code-block:: js

        {"items": [
            {"id": "cool.guy@gmail.com"}
        ]}

    """
    rows = Subscription.query(
        request.registry['godhand:db'],
        subscriber_id=request.authenticated_userid)
    return {'items': [x.as_dict() for x in rows]}


class PutSubscriptionsSchema(co.MappingSchema):
    action = co.SchemaNode(
        co.String(), validator=co.OneOf(['allow', 'block', 'clear']))
    user_id = co.SchemaNode(co.String(), validator=co.Email())


@subscriptions.put(schema=PutSubscriptionsSchema)
def update_subscriptions(request):
    """ Update subscription status for a user.

    If ``allow`` is sent for ``cool.user@gmail.com``, we are requesting access
    to their volumes and they will see us in ``subscription_requests``. Note
    that they will need to use ``PUT /account/subscribers`` as well to give us
    access.

    Sending ``block`` will remove them from your ``subscriber_requests``.

    Sending ``clear`` will remove your preference. If a subscription is
    requested, it will show up again in your ``subscriber_requests``.

    """
    db = request.registry['godhand:db']
    v = request.validated
    Subscription.retrieve(
        request.registry['godhand:db'],
        publisher_id=v['user_id'],
        subscriber_id=request.authenticated_userid
    ).update_subscriber_status(db, v['action'])


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


@volume.put(schema=PutVolumeSchema, permission='write')
def update_volume_meta(request):
    """ Update volume metadata.
    """
    keys = ('language', 'volume_number')
    db = request.registry['godhand:db']
    volume = request.validated['volume']
    volume.update_meta(db, **{k: request.validated[k] for k in keys})


@volume.delete(permission='write')
def delete_volume(request):
    """ Delete volume.
    """
    request.validated['volume'].delete(request.registry['godhand:db'])


@volume_cover.get(schema=VolumePathSchema)
def get_volume_cover(request):
    """ Get a volume page.
    """
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
    attachment = request.registry['godhand:db'].get_attachment(
        request.validated['volume'].id,
        request.validated['filename'],
    )
    if attachment is None:
        raise HTTPNotFound()
    response = request.response
    response.body_file = attachment
    return response


@volume_file.delete(schema=VolumeFileSchema, permission='write')
def delete_volume_file(request):
    """ Delete file of volume.
    """
    request.validated['volume'].delete_file(
        request.registry['godhand:db'], request.validated['filename'])


class StoreReaderProgressSchema(VolumePathSchema):
    page_number = co.SchemaNode(co.Integer(), validator=co.Range(min=0))


@volume_bookmark.put(schema=StoreReaderProgressSchema)
def update_volume_bookmark(request):
    """ Update bookmark for volume.
    """
    Bookmark.update(
        db=request.registry['godhand:db'],
        user_id=request.authenticated_userid,
        volume=request.validated['volume'],
        page_number=request.validated['page_number'],
    )
