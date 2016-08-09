import os
import time
import unittest

import couchdb.client

from godhand.rest.tests.utils import AppTestFixture
from godhand.models.series import Series
from godhand.utils import wait_for_couchdb

HERE = os.path.dirname(__file__)


class CliTestFixture(AppTestFixture):
    @property
    def compose_file(self):
        return os.path.join(HERE, 'docker-compose.cli.yml')


class TestFuseSync(unittest.TestCase):
    def setUp(self):
        from godhand import cli
        self.app_test_fix = self.use_fixture(CliTestFixture())
        self.fuse_url = 'http://{}:8000/api'.format(self.app_test_fix.get_ip())
        self.couchdb_url = 'http://couchdb:mypassword@{}:8001'.format(
            self.app_test_fix.get_ip())
        self.cli = cli
        wait_for_couchdb(self.couchdb_url)

    def use_fixture(self, fix):
        self.addCleanup(fix.cleanUp)
        fix.setUp()
        return fix

    def test_sync(self):
        time.sleep(10)
        self.cli.fuse_setup(self.fuse_url)
        db = couchdb.client.Server(self.couchdb_url).create('godhand')
        Series.by_id.sync(db)
        with open(os.path.join(HERE, 'manga.json')) as f:
            self.cli.upload(self.couchdb_url, self.fuse_url, f)
        self.cli.fuse_sync(
            self.couchdb_url,
            self.fuse_url,
        )
