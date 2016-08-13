from functools import partial

from cornice import Service
from pyramid.security import Allow
from pyramid.security import Everyone


def groupfinder(userid, request):
    return [userid]


def default_acl(request):
    return [
        (Allow, Everyone, ('view', 'write')),
    ]


GodhandService = partial(Service, acl=default_acl, permission='view')
