import colander as co

from ..models import Subscription
from .utils import GodhandService


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
