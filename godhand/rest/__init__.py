import os
import re

from pyramid.config import Configurator
import couchdb.client

from ..utils import wait_for_couchdb


def main(global_config, books_path, couchdb_url, **settings):
    books_path = os.path.abspath(books_path)
    config = Configurator(settings=settings)
    config.include('cornice')
    config.scan('.', ignore=[re.compile('^.*tests$').match])
    wait_for_couchdb(couchdb_url)
    client = couchdb.client.Server(couchdb_url)
    try:
        db = client.create('godhand')
    except couchdb.http.PreconditionFailed:
        db = client['godhand']
    config.registry['godhand:books_path'] = books_path
    config.registry['godhand:db'] = db
    config.add_static_view('static', books_path)
    return config.make_wsgi_app()
