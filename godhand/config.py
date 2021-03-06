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

    def __init__(self, couchdb_url,
                 google_client_appname, google_client_id, google_client_secret,
                 auth_secret, root_email, disable_auth, token_secret):
        self.disable_auth = disable_auth
        self.couchdb_url = couchdb_url
        self.auth_secret = auth_secret
        self.google_client_appname = google_client_appname
        self.google_client_id = google_client_id
        self.google_client_secret = google_client_secret
        self.root_email = root_email
        self.token_secret = token_secret

    def __repr__(self):
        attributes = ['{}={!r}'.format(k, getattr(self, k)) for k in (
            'couchdb_url', 'disable_auth')]
        return 'GodhandConfiguration<{}>'.format(
            ','.join(attributes)
        )


def is_path(node, appstruct):
    if not os.path.exists(appstruct):
        raise co.Invalid(node, 'Path does not exist.')


class GodhandConfigurationSchema(co.MappingSchema):
    couchdb_url = co.SchemaNode(co.String(), validator=co.url)
    disable_auth = co.SchemaNode(co.Boolean(), missing=False)
    google_client_appname = co.SchemaNode(co.String(), missing=None)
    google_client_id = co.SchemaNode(co.String(), missing=None)
    google_client_secret = co.SchemaNode(co.String(), missing=None)
    auth_secret = co.SchemaNode(co.String())
    token_secret = co.SchemaNode(co.String())
    root_email = co.SchemaNode(co.String())
