from subprocess import check_call
from tempfile import SpooledTemporaryFile
from urllib.parse import urlparse
import logging
import os

from godhand.utils import wait_for_couchdb


GODHAND_COUCHDB_URL = os.environ.get('TEST_GODHAND_COUCHDB_URL')
here = os.path.dirname(__file__)
docker_compose_file = os.path.join(here, 'docker-compose.yml')


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


def setup_standard():
    compose_cmd = DockerCompose(docker_compose_file)
    compose_cmd('up', '-d')
    wait_for_couchdb(get_couchdb_url())


def teardown_standard():
    compose_cmd = DockerCompose(docker_compose_file)
    compose_cmd('stop', '--timeout', '0')
    compose_cmd('rm', '-fv', '--all')
