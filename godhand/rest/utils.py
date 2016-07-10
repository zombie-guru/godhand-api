from pyramid.httpexceptions import HTTPNotFound
import colander as co


class PaginationSchema(co.MappingSchema):
    limit = co.SchemaNode(
        co.Integer(), missing=10, validator=co.Range(min=0, max=100),
        location='querystring')
    offset = co.SchemaNode(
        co.Integer(), missing=0, validator=co.Range(min=0),
        location='querystring')


def paginate_query(request, query, preparer, key):
    v = request.validated
    rows = query.limit(v['limit']).offset(v['offset'])
    return {
        key: [preparer(x) for x in rows],
        'limit': v['limit'],
        'offset': v['offset'],
        'total': query.count(),
    }


def sqlalchemy_preparer(model):
    def preparer(id):
        instance = model.from_id(id)
        if instance is None:
            raise HTTPNotFound()
        return instance
    return preparer


def sqlalchemy_path_schemanode(model):
    return co.SchemaNode(
        co.Integer(),
        location='path',
        preparer=sqlalchemy_preparer(model),
    )
