from PIL import Image
from tempfile import NamedTemporaryFile
from tempfile import TemporaryFile
import contextlib
import logging
import os
import tarfile
import unittest
import zipfile

from fixtures import TempDir
from webtest import TestApp
import couchdb.client
import couchdb.http
import mock

from godhand.tests.utils import get_docker_ip


HERE = os.path.dirname(__file__)
BUILDOUT_DIR = os.environ['BUILDOUT_DIRECTORY']
BUILDOUT_BIN_DIRECTORY = os.environ['BUILDOUT_BIN_DIRECTORY']
LOG = logging.getLogger('tests')


class ApiTest(unittest.TestCase):
    maxDiff = 5000
    root_email = 'root@domain.com'
    client_appname = 'my-client-appname'
    client_id = 'my-client-id'
    client_secret = 'my-client-secret'
    couchdb_url = 'http://couchdb:mypassword@{}:8001'.format(get_docker_ip())

    def setUp(self):
        from godhand.rest import main
        base_path = self.use_fixture(TempDir()).path
        self.books_path = books_path = os.path.join(base_path, 'books')
        os.makedirs(books_path)
        self.api = TestApp(main(
            {},
            books_path=books_path,
            couchdb_url=self.couchdb_url,
            google_client_appname=self.client_appname,
            google_client_id=self.client_id,
            google_client_secret=self.client_secret,
            auth_secret='my-auth-secret',
            root_email=self.root_email,
        ))
        self.db = couchdb.client.Server(self.couchdb_url)['godhand']
        self.addCleanup(self._cleanDb)

    def use_fixture(self, fix):
        self.addCleanup(fix.cleanUp)
        fix.setUp()
        return fix

    def _cleanDb(self):
        client = couchdb.client.Server(self.couchdb_url)
        for dbname in ('godhand', 'auth', 'derp'):
            try:
                client.delete(dbname)
            except couchdb.http.ResourceNotFound:
                pass

    def oauth2_login(self, email):
        state = self.api.get('/oauth-init').json_body.pop('state')
        with mock.patch('godhand.rest.auth.client') as client:
            with mock.patch('godhand.rest.auth.requests') as requests:
                expected = {
                    'client_id': self.client_id,
                    'application_name': self.client_appname,
                    'scope': 'openid email',
                    'redirect_uri': 'http://localhost/oauth-callback',
                    'login_hint': '',
                }
                response = self.api.get('/oauth-init').json_body
                state = response.pop('state')
                assert state
                assert expected == response

                requests.post.return_value.status_code = 200
                requests.post.return_value.json.return_value = {
                    'id_token': 'myidtoken',
                }
                client.verify_id_token.return_value = {
                    'email_verified': True, 'email': email,
                }

                expected = {'email': email}
                response = self.api.get(
                    '/oauth-callback',
                    params={'state': state, 'code': 'mycode'},
                ).json_body
                assert expected == response

                requests.post.assert_called_once_with(
                    'https://www.googleapis.com/oauth2/v4/token',
                    data={
                        'code': 'mycode',
                        'state': state,
                        'client_id': self.client_id,
                        'client_secret': self.client_secret,
                        'redirect_uri': 'http://localhost/oauth-callback',
                        'grant_type': 'authorization_code',
                    },
                )


class RootLoggedInTest(ApiTest):
    def setUp(self):
        super(RootLoggedInTest, self).setUp()
        self.oauth2_login(self.root_email)


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
