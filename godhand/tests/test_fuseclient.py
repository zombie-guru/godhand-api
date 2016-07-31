import os
import unittest

from godhand.rest.tests.utils import AppTestFixture

HERE = os.path.dirname(__file__)


class FuseTestFixture(AppTestFixture):
    @property
    def compose_file(self):
        return os.path.join(HERE, 'docker-compose.yml')


class TestFuseClient(unittest.TestCase):
    def setUp(self):
        from godhand.fuseclient import FuseClient
        self.app_test_fix = self.use_fixture(FuseTestFixture())
        self.client = FuseClient('http://{}:8000/api'.format(
            self.app_test_fix.get_ip()))

    def use_fixture(self, fix):
        self.addCleanup(fix.cleanUp)
        fix.setUp()
        return fix

    def test_setup_fuse(self):
        self.client.setup_fuse()
        self.client.start_fuse()
        self.client.wait_until_ready()
        assert self.client.get_status()['ready']
        self.client.update(
            [{'fuse:type': 'series', 'genres': ['a', 'b', 'c']}], True)
        self.client.update(
            [{'fuse:type': 'series', 'genres': ['a', 'b', 'c']}], False)
        self.client.stop_fuse()
        assert not self.client.get_status()['ready']
