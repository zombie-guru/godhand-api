import colander as co

from ..models.user import UserSettings
from ..models.volume import Volume
from .utils import GodhandService


account = GodhandService(
    name='account',
    path='/account',
)
subscribers = GodhandService(
    name='account subscribers',
    path='/account/subscribers',
)
subscriber = GodhandService(
    name='account subscriber',
    path='/account/subscribers/{subscriber}',
)


@account.get()
def get_account_info(request):
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


@subscribers.get()
def get_subscribers(request):
    db = request.registry['godhand:db']
    settings = UserSettings.for_user(db, request.authenticated_userid)
    return {'items': settings.subscribers}


class SubscriberSchema(co.MappingSchema):
    subscriber = co.SchemaNode(
        co.String(), location='path', validator=co.Email())


@subscriber.put(schema=SubscriberSchema)
def add_subscriber(request):
    db = request.registry['godhand:db']
    settings = UserSettings.for_user(db, request.authenticated_userid)
    settings.add_subscriber(db, request.validated['subscriber'])


@subscriber.delete(schema=SubscriberSchema)
def remove_subscriber(request):
    db = request.registry['godhand:db']
    settings = UserSettings.for_user(db, request.authenticated_userid)
    settings.remove_subscriber(db, request.validated['subscriber'])
