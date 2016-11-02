from ..models.user import UserSettings
from .utils import GodhandService


user = GodhandService(
    name='user-info',
    path='/user',
    permission='authenticate',
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
        'permissions': {
            k: bool(request.has_permission(k))
            for k in ('view', 'write', 'admin')
        },
        'user_id': request.authenticated_userid,
        'language': settings.language if settings else None,
    }
