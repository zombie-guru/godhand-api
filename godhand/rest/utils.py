from functools import partial

from cornice import Service
from pyramid.httpexceptions import HTTPUnauthorized


def is_logged_in(request):
    if request.registry['godhand:cfg'].disable_auth:
        return
    if request.authenticated_userid is None:
        raise HTTPUnauthorized()


AuthenticatedService = partial(Service, acl=is_logged_in)
