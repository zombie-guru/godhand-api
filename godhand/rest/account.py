import colander as co

from ..models.user import UserSettings
from ..models.volume import Volume
from .utils import GodhandService


class UserPathSchema(co.MappingSchema):
    user = co.SchemaNode(co.String(), location="path", validator=co.Email())


account = GodhandService(
    name='account',
    path='/account',
    permission=None,
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
