import os
import re

from pyramid.config import Configurator
import couchdb.client

from ..config import GodhandConfiguration
from ..utils import wait_for_couchdb


def main(global_config, **settings):
    cfg = GodhandConfiguration.from_env(
        books_path=settings.get('books_path', None),
        couchdb_url=settings.get('couchdb_url', None),
        fuse_url=settings.get('fuse_url', None),
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
    config.registry['godhand:books_path'] = books_path
    config.registry['godhand:db'] = db
    config.add_static_view('static', books_path)
    return config.make_wsgi_app()
