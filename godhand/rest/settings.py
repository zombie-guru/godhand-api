import colander as co

from ..models.user import UserSettings
from .utils import GodhandService


subscribers = GodhandService(
    name='account subscribers',
    path='/account/subscribers',
)
subscriber = GodhandService(
    name='account subscriber',
    path='/account/subscribers/{subscriber}',
)
subscribed = GodhandService(
    name='account subscribed',
    path='/account/subscribed',
)


@subscribers.get()
def get_subscribers(request):
    db = request.registry['godhand:db']
    settings = UserSettings.for_user(db, request.authenticated_userid)
    return {'items': settings.subscribers}


class PutSubscriberSchema(co.MappingSchema):
    subscriber = co.SchemaNode(
        co.String(), location='path', validator=co.Email())


@subscriber.put(schema=PutSubscriberSchema)
def add_subscriber(request):
    db = request.registry['godhand:db']
    settings = UserSettings.for_user(db, request.authenticated_userid)
    settings.add_subscriber(db, request.validated['subscriber'])


@subscribed.get()
def get_subcribed(request):
    return {
        'items': UserSettings.get_subscribed_owner_ids(
            request.registry['godhand:db'], request.authenticated_userid)
    }
