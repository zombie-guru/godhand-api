from subprocess import check_call
from tempfile import SpooledTemporaryFile
from tempfile import TemporaryFile
from urllib.parse import urlparse
import contextlib
import logging
import os
import tarfile
import unittest

from fixtures import Fixture
from fixtures import TempDir
from webtest import TestApp


BUILDOUT_DIR = os.environ['BUILDOUT_DIRECTORY']
BUILDOUT_BIN_DIRECTORY = os.environ['BUILDOUT_BIN_DIRECTORY']
LOG = logging.getLogger('tests')


class AppTestFixture(Fixture):
    def _setUp(self):
        self.addCleanup(self.cleanUp)
        self.compose('up', '-d')

    def get_ip(self):
        try:
            url = os.environ['DOCKER_HOST']
        except KeyError:
            return '127.0.0.1'
        else:
            return urlparse(url).hostname

    def cleanUp(self):
        self.compose('stop', '--timeout', '0')
        self.compose('rm', '-fv', '--all')

    def compose(self, *args):
        with SpooledTemporaryFile() as f:
            check_call((
                os.path.join(BUILDOUT_BIN_DIRECTORY, 'docker-compose'),
                ) + args, cwd=BUILDOUT_DIR, stderr=f, stdout=f)
            f.flush()
            f.seek(0)
            LOG.debug(f.read())


class ApiTest(unittest.TestCase):
    maxDiff = 5000

    def setUp(self):
        from godhand.rest import main
        base_path = self.use_fixture(TempDir()).path
        self.books_path = books_path = os.path.join(base_path, 'books')
        os.makedirs(books_path)
        self.app_test_fix = self.use_fixture(AppTestFixture())
        self.api = TestApp(main(
            {}, books_path=books_path,
            couchdb_url='http://couchdb:mypassword@{}:8001'.format(
                self.app_test_fix.get_ip())
        ))

    def use_fixture(self, fix):
        self.addCleanup(fix.cleanUp)
        fix.setUp()
        return fix


@contextlib.contextmanager
def tmp_cbt(filenames):
    with TemporaryFile() as f:
        with tarfile.open(fileobj=f, mode='w') as ar:
            for filename in filenames:
                with TemporaryFile() as mf:
                    content = 'content of {}'.format(filename).encode('utf-8')
                    mf.write(content)
                    mf.flush()
                    mf.seek(0)
                    info = tarfile.TarInfo(filename)
                    info.size = len(content)
                    ar.addfile(info, mf)
        f.flush()
        f.seek(0)
        yield f
