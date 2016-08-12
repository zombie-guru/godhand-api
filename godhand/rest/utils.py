from functools import partial

from cornice import Service
from pyramid.httpexceptions import HTTPUnauthorized
import colander as co


def is_logged_in(request):
    if request.registry['godhand:cfg'].disable_auth:
        return
    if request.authenticated_userid is None:
        raise HTTPUnauthorized()


AuthenticatedService = partial(Service, acl=is_logged_in)


class PaginationSchema(co.MappingSchema):
    offset = co.SchemaNode(
        co.Integer(), missing=0, validator=co.Range(min=0),
        location='querystring')
    limit = co.SchemaNode(
        co.Integer(), missing=10, validator=co.Range(min=1, max=50),
        location='querystring')


def paginate_query(request, view_def, key, start=None, end=None):
    v = request.validated
    db = request.registry['godhand:db']
    rows = view_def(
        db, skip=v['offset'], limit=v['limit'], startkey=start, endkey=end)
    return {
        key: [dict(x.items()) for x in rows],
        'offset': rows.offset,
        'limit': v['limit'],
        'total': rows.total_rows,
    }
