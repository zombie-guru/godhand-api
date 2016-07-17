import colander as co


class PaginationSchema(co.MappingSchema):
    offset = co.SchemaNode(
        co.Integer(), missing=0, validator=co.Range(min=0),
        location='querystring')


def paginate_query(request, query, key):
    v = request.validated
    db = request.registry['godhand:db']
    rows = db.query(query, offset=v['offset'])
    return {
        key: [x['key'] for x in rows],
        'offset': rows.offset,
        'total': rows.total_rows,
    }
