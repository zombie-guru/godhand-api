from subprocess import check_call
from tempfile import SpooledTemporaryFile
from urllib.parse import urlparse
import logging
import os


GODHAND_COUCHDB_URL = os.environ.get('TEST_GODHAND_COUCHDB_URL')


class DockerCompose(object):
    log = logging.getLogger('docker-compose')

    def __init__(self, compose_file):
        self.compose_file = compose_file

    def __call__(self, *args):
        if GODHAND_COUCHDB_URL:
            self.log.info('skipping fixture call - couchdb setup externally.')
            return
        with SpooledTemporaryFile() as f:
            check_call((
                'docker-compose',
                '-f', self.compose_file,
                '--project', 'testing',
                ) + args, stderr=f, stdout=f)
            f.flush()
            f.seek(0)
            self.log.debug(f.read())


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
