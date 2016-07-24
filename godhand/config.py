import os

import colander as co


class GodhandConfiguration(object):
    @classmethod
    def from_env(cls, **kws):
        kws = {k: v for k, v in kws.items() if v is not None}
        kws = dict(cls.kws_from_env(), **kws)
        kws = GodhandConfigurationSchema().deserialize(kws)
        return cls(**kws)

    @classmethod
    def kws_from_env(cls, prefix='GODHAND_'):
        kws = filter(lambda x: x.startswith(prefix), os.environ.keys())
        return {
            kw[len(prefix):].lower(): os.environ[kw]
            for kw in kws
        }

    def __init__(self, couchdb_url, books_path):
        self.couchdb_url = couchdb_url
        self.books_path = books_path

    def __repr__(self):
        attributes = ['{}={!r}'.format(k, getattr(self, k)) for k in (
            'couchdb_url', 'books_path')]
        return 'GodhandConfiguration<{}>'.format(
            ','.join(attributes)
        )


def is_path(node, appstruct):
    if not os.path.exists(appstruct):
        raise co.Invalid(node, 'Path does not exist.')


class GodhandConfigurationSchema(co.MappingSchema):
    couchdb_url = co.SchemaNode(co.String(), validator=co.url)
    books_path = co.SchemaNode(co.String(), validator=is_path)
