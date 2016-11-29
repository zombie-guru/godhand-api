from ..models.user import UserSettings
from ..models.volume import Volume
from .utils import GodhandService


user = GodhandService(
    name='user-info',
    path='/user',
)

user_usage = GodhandService(
    name='user_usage',
    path='/user/usage',
)


@user.get()
def get_user_info(request):
    settings = None
    if request.authenticated_userid:
        settings = UserSettings.for_user(
            request.registry['godhand:db'], request.authenticated_userid)
    logged_in = request.authenticated_userid is not None
    auth_disabled = request.registry['godhand:cfg'].disable_auth
    return {
        'needs_authentication': not auth_disabled and not logged_in,
        'subscribed_ids': UserSettings.get_subscribed_owner_ids(
            request.registry['godhand:db'], request.authenticated_userid),
        'user_id': request.authenticated_userid,
        'language': settings.language if settings else None,
    }


@user_usage.get()
def get_user_usage(request):
    return {
        'usage': Volume.get_user_usage(
            request.registry['godhand:db'], request.authenticated_userid)
    }
