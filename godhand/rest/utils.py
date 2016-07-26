import colander as co


class PaginationSchema(co.MappingSchema):
    offset = co.SchemaNode(
        co.Integer(), missing=0, validator=co.Range(min=0),
        location='querystring')
    limit = co.SchemaNode(
        co.Integer(), missing=10, validator=co.Range(min=1, max=50),
        location='querystring')


def paginate_query(request, query, key):
    v = request.validated
    db = request.registry['godhand:db']
    rows = db.query(query, skip=v['offset'], limit=v['limit'])
    return {
        key: [x['key'] for x in rows],
        'offset': rows.offset,
        'limit': v['limit'],
        'total': rows.total_rows,
    }
