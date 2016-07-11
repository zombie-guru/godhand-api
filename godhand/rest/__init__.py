import re

from pyramid.config import Configurator
from godhand.models import init_db


def main(global_config, books_path, sqlalchemy_url, **settings):
    init_db(sqlalchemy_url)
    config = Configurator(settings=settings)
    config.include('cornice')
    config.include('pyramid_tm')
    config.scan('.', ignore=[re.compile('^.*tests$').match])
    config.registry['godhand:books_path'] = books_path
    return config.make_wsgi_app()
