from functools import partial

from cornice import Service
from pyramid.security import Allow
from pyramid.security import Deny
from pyramid.security import Everyone

from godhand.models.auth import User


def groupfinder(userid, request):
    authdb = request.registry['godhand:authdb']
    user = User.by_email(authdb, key=userid, limit=1).rows
    if len(user) == 0:
        return []
    user = user[0]
    return [
        user.email,
    ] + ['group:{}'.format(x) for x in user.groups]


def default_acl(request):
    return [
        (Allow, 'group:user', ('view',)),
        (Allow, 'group:admin', ('write', 'view', 'admin')),
        (Allow, Everyone, ('authenticate',)),
        (Deny, Everyone, ('view', 'write')),
    ]


GodhandService = partial(Service, acl=default_acl, permission='view')
