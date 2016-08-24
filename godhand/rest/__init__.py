import re

from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.config import Configurator
from pyramid.session import SignedCookieSessionFactory
import couchdb.client
import couchdb.http
import pyramid.security

from ..config import GodhandConfiguration
from ..models.auth import User
from ..utils import wait_for_couchdb
from .utils import groupfinder


def main(global_config, **settings):
    cfg = GodhandConfiguration.from_env(
        couchdb_url=settings.get('couchdb_url', None),
        disable_auth=settings.get('disable_auth', None),
        google_client_id=settings.get('google_client_id'),
        google_client_secret=settings.get('google_client_secret'),
        google_client_appname=settings.get('google_client_appname'),
        auth_secret=settings.get('auth_secret'),
        root_email=settings.get('root_email'),
    )
    config = Configurator(settings=settings)
    setup_db(config, cfg.couchdb_url, cfg.root_email)
    setup_acl(config, cfg.auth_secret)
    config.include('cornice')
    config.scan('.', ignore=[re.compile('^.*tests$').match])
    config.registry['godhand:cfg'] = cfg
    config.add_route(
        'google-oauth2', 'https://accounts.google.com/o/oauth2/v2/auth')
    return config.make_wsgi_app()


def setup_db(config, couchdb_url, root_email):
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
    root = User.load(authdb, 'user:root')
    if root is None:
        root = User(id='user:root')
    root.email = root_email
    root.groups = ['admin', 'user']
    root.store(authdb)
    User.by_email.sync(authdb)


def setup_acl(config, secret):
    config.set_authorization_policy(ACLAuthorizationPolicy())
    config.set_authentication_policy(AuthTktAuthenticationPolicy(
        secret, callback=groupfinder, hashalg='sha512'))
    config.set_session_factory(SignedCookieSessionFactory(secret))
    config.set_default_permission('edit')


def has_permission(request, permission, context=None):
    if context is None:
        context = request.context
    return pyramid.security.has_permission(permission, context, request)
