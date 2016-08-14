from couchdb.mapping import Document


class GodhandDocument(Document):
    @classmethod
    def _wrap_row(cls, row):
        wrapped = super(GodhandDocument, cls)._wrap_row(row)
        wrapped.key = row['key']
        return wrapped
