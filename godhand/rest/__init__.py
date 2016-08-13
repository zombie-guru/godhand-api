import os
import re

from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.config import Configurator
from pyramid.session import SignedCookieSessionFactory
import couchdb.client
import couchdb.http

from ..config import GodhandConfiguration
from ..utils import wait_for_couchdb


def main(global_config, **settings):
    cfg = GodhandConfiguration.from_env(
        books_path=settings.get('books_path', None),
        couchdb_url=settings.get('couchdb_url', None),
        disable_auth=settings.get('disable_auth', None),
        google_client_id=settings.get('google_client_id'),
        google_client_secret=settings.get('google_client_secret'),
        google_client_appname=settings.get('google_client_appname'),
        auth_secret=settings.get('auth_secret'),
    )
    books_path = os.path.abspath(cfg.books_path)
    config = Configurator(settings=settings)
    config.include('cornice')
    config.scan('.', ignore=[re.compile('^.*tests$').match])
    wait_for_couchdb(cfg.couchdb_url)
    client = couchdb.client.Server(cfg.couchdb_url)
    try:
        db = client.create('godhand')
    except couchdb.http.PreconditionFailed:
        db = client['godhand']
    try:
        authdb = client.create('auth')
    except couchdb.http.PreconditionFailed:
        authdb = client['auth']
    config.registry['godhand:books_path'] = books_path
    config.registry['godhand:db'] = db
    config.registry['godhand:authdb'] = authdb
    config.registry['godhand:cfg'] = cfg
    if not cfg.disable_auth:
        setup_acl(config, cfg.auth_secret)
    config.add_static_view('static', books_path)
    return config.make_wsgi_app()


def setup_acl(config, secret):
    authz_policy = ACLAuthorizationPolicy()
    config.set_authorization_policy(authz_policy)
    authn_policy = AuthTktAuthenticationPolicy(secret, hashalg='sha512')
    config.set_authentication_policy(authn_policy)
    session_factory = SignedCookieSessionFactory(secret)
    config.set_session_factory(session_factory)
