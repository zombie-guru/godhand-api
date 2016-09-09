from subprocess import check_call
from tempfile import SpooledTemporaryFile
from urllib.parse import urlparse
import logging
import os


class DockerCompose(object):
    log = logging.getLogger('docker-compose')

    def __init__(self, compose_file):
        self.compose_file = compose_file

    def get_ip(self):
        return get_docker_ip()

    def __call__(self, *args):
        with SpooledTemporaryFile() as f:
            check_call((
                'docker-compose',
                '-f', self.compose_file,
                '--project', 'testing',
                ) + args, stderr=f, stdout=f)
            f.flush()
            f.seek(0)
            self.log.debug(f.read())


def get_docker_ip():
    try:
        url = os.environ['DOCKER_HOST']
    except KeyError:
        return '127.0.0.1'
    else:
        return urlparse(url).hostname
