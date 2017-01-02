import logging

from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.config import Configurator
from pyramid.session import SignedCookieSessionFactory
import couchdb.client
import couchdb.http

from .config import GodhandConfiguration
from .models import init_views
from .models import Subscription
from .utils import owner_group
from .utils import subscription_group
from .utils import wait_for_couchdb


def setup_godhand_config(config):
    settings = config.get_settings()
    cfg = GodhandConfiguration.from_env(
        couchdb_url=settings.get('couchdb_url', None),
        disable_auth=settings.get('disable_auth', None),
        google_client_id=settings.get('google_client_id'),
        google_client_secret=settings.get('google_client_secret'),
        google_client_appname=settings.get('google_client_appname'),
        auth_secret=settings.get('auth_secret'),
        root_email=settings.get('root_email'),
        token_secret=settings.get('token_secret'),
    )
    config.registry['godhand:cfg'] = cfg


def main(global_config, **settings):
    logging.getLogger('PIL.PngImagePlugin').setLevel('INFO')
    logging.getLogger('PIL.Image').setLevel('INFO')

    config = Configurator(settings=settings)
    config.include('cornice')
    setup_godhand_config(config)
    setup_db(config)
    config.include('godhand.auth')
    setup_acl(config)
    config.scan('.views')
    return config.make_wsgi_app()


def setup_db(config):
    couchdb_url = config.registry['godhand:cfg'].couchdb_url
    wait_for_couchdb(couchdb_url)
    client = couchdb.client.Server(couchdb_url)
    try:
        db = client.create('godhand')
    except couchdb.http.PreconditionFailed:
        db = client['godhand']
    try:
        authdb = client.create('auth')
    except couchdb.http.PreconditionFailed:
        authdb = client['auth']
    config.registry['godhand:db'] = db
    config.registry['godhand:authdb'] = authdb
    init_views(db)


def groupfinder(userid, request):
    subscriptions = Subscription.query(
        request.registry['godhand:db'], subscriber_id=userid)
    return [
        owner_group(userid)
    ] + [
        subscription_group(x.publisher_id) for x in subscriptions
    ]


def setup_acl(config):
    secret = config.registry['godhand:cfg'].auth_secret
    config.set_authorization_policy(ACLAuthorizationPolicy())
    config.set_authentication_policy(AuthTktAuthenticationPolicy(
        secret, callback=groupfinder, hashalg='sha512'))
    config.set_session_factory(SignedCookieSessionFactory(secret))
