from PIL import Image
from subprocess import check_call
from tempfile import NamedTemporaryFile
from tempfile import SpooledTemporaryFile
from tempfile import TemporaryFile
from urllib.parse import urlparse
import contextlib
import logging
import os
import tarfile
import unittest
import zipfile

from fixtures import Fixture
from fixtures import TempDir
from webtest import TestApp
import couchdb.client


HERE = os.path.dirname(__file__)
BUILDOUT_DIR = os.environ['BUILDOUT_DIRECTORY']
BUILDOUT_BIN_DIRECTORY = os.environ['BUILDOUT_BIN_DIRECTORY']
LOG = logging.getLogger('tests')


class AppTestFixture(Fixture):
    def _setUp(self):
        self.addCleanup(self.cleanUp)
        self.compose('up', '-d')

    @property
    def compose_file(self):
        return os.path.join(HERE, 'docker-compose.yml')

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
                '-f', self.compose_file,
                '--project', 'testing',
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
        self.api = TestApp(main({}, books_path=books_path, **self.envvars))
        self.db = couchdb.client.Server(self.envvars['couchdb_url'])['godhand']

    def use_fixture(self, fix):
        self.addCleanup(fix.cleanUp)
        fix.setUp()
        return fix

    @property
    def envvars(self):
        return {
            'couchdb_url': 'http://couchdb:mypassword@{}:8001'.format(
                self.app_test_fix.get_ip()),
            'disable_auth': True,
        }


class ApiTestWithAuth(ApiTest):
    client_appname = 'my-client-appname'
    client_id = 'my-client-id'
    client_secret = 'my-client-secret'

    @property
    def envvars(self):
        return {
            'couchdb_url': 'http://couchdb:mypassword@{}:8001'.format(
                self.app_test_fix.get_ip()),
            'disable_auth': False,
            'google_client_appname': self.client_appname,
            'google_client_id': self.client_id,
            'google_client_secret': self.client_secret,
            'auth_secret': 'my-auth-secret',
        }


@contextlib.contextmanager
def tmp_cbt(filenames):
    with TemporaryFile() as f:
        with tarfile.open(fileobj=f, mode='w') as ar:
            for filename in filenames:
                with NamedTemporaryFile() as mf:
                    im = Image.new('RGB', (128, 128), 'white')
                    im.putpixel((0, 0), (0, 0, 0))
                    im.save(mf, 'jpeg')
                    mf.flush()
                    ar.add(mf.name, filename)
        f.flush()
        f.seek(0)
        yield f


class CbtFile(object):
    ext = '.cbt'

    @property
    def pages(self):
        widths = (256, 128, 64)
        heights = (128, 128, 128)
        orientation = ('horizontal', 'horizontal', 'vertical')
        return [{
            'filename': 'page-{:x}.png'.format(n),
            'width': widths[n % 3],
            'height': heights[n % 3],
            'orientation': orientation[n % 3],
            'black_pixel': (n, n),
        } for n in range(15)]

    @contextlib.contextmanager
    def packaged(self):
        with TemporaryFile() as f:
            with tarfile.open(fileobj=f, mode='w') as ar:
                for o in self.pages:
                    with NamedTemporaryFile() as mf:
                        im = Image.new(
                            'RGB', (o['width'], o['height']))
                        im.putpixel(o['black_pixel'], (0xfe, 0xfe, 0xfe))
                        im.save(mf, 'png')
                        mf.flush()
                        ar.add(mf.name, o['filename'])
            f.flush()
            f.seek(0)
            yield f


class CbzFile(CbtFile):
    ext = '.cbz'

    @contextlib.contextmanager
    def packaged(self):
        with TemporaryFile() as f:
            with zipfile.ZipFile(f, mode='w') as ar:
                for o in self.pages:
                    with NamedTemporaryFile() as mf:
                        im = Image.new(
                            'RGB', (o['width'], o['height']))
                        im.putpixel(o['black_pixel'], (0xfe, 0xfe, 0xfe))
                        im.save(mf, 'png')
                        mf.flush()
                        ar.write(mf.name, o['filename'])
            f.flush()
            f.seek(0)
            yield f
