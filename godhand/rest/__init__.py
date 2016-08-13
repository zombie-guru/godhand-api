import os
import re

from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.config import Configurator
import couchdb.client
import couchdb.http

from ..config import GodhandConfiguration
from ..utils import wait_for_couchdb
from .utils import groupfinder


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
    setup_db(config, cfg.couchdb_url)
    setup_acl(config, cfg.auth_secret)
    config.include('cornice')
    config.scan('.', ignore=[re.compile('^.*tests$').match])
    config.registry['godhand:books_path'] = books_path
    config.registry['godhand:cfg'] = cfg
    config.add_static_view('static', books_path)
    return config.make_wsgi_app()


def setup_db(config, couchdb_url):
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


def setup_acl(config, secret):
    authz_policy = ACLAuthorizationPolicy()
    config.set_authorization_policy(authz_policy)
    config.set_authentication_policy(AuthTktAuthenticationPolicy(
        secret, callback=groupfinder, hashalg='sha512'))
