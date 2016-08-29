import os

from godhand.tests.utils import DockerCompose

here = os.path.dirname(__file__)
docker_compose_file = os.path.join(here, 'docker-compose.yml')
compose_cmd = DockerCompose(docker_compose_file)


def setup():
    compose_cmd('up', '-d')


def teardown():
    compose_cmd('stop', '--timeout', '0')
    compose_cmd('rm', '-fv', '--all')
