""" godhand.auth

This subproject only manages oauth interactions that set authenticated_userid.

"""
from pyramid.config import Configurator
import couchdb.client
import couchdb.http

from godhand import setup_godhand_config


def includeme(config):
    cfg = config.registry['godhand:cfg']
    setup_db(config, cfg.couchdb_url, cfg.root_email)
    config.scan('.views')
    config.add_route(
        'google-oauth2', 'https://accounts.google.com/o/oauth2/v2/auth')


def main(global_config, **settings):
    config = Configurator(settings=settings)
    config.include('cornice')
    setup_godhand_config(config)
    config.include('godhand.auth')
    return config.make_wsgi_app()


def setup_db(config, couchdb_url, root_email):
    client = couchdb.client.Server(couchdb_url)
    try:
        db = client.create('auth')
    except couchdb.http.PreconditionFailed:
        db = client['auth']
    config.registry['godhand:authdb'] = db
