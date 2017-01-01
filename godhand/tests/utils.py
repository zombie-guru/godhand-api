from urllib.parse import urlparse
import os


GODHAND_COUCHDB_URL = os.environ.get('TEST_GODHAND_COUCHDB_URL')


def get_couchdb_url():
    if GODHAND_COUCHDB_URL:
        return GODHAND_COUCHDB_URL
    return 'http://couchdb:mypassword@{}:8001'.format(_get_docker_ip())


def _get_docker_ip():
    try:
        url = os.environ['DOCKER_HOST']
    except KeyError:
        return '127.0.0.1'
    else:
        return urlparse(url).hostname
