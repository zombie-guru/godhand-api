from urllib.parse import urlparse
from urllib.parse import parse_qs
import os
import unittest

from webtest import TestApp
import couchdb.client
import couchdb.http
import mock

from godhand.tests.fakevolumes import CbtFile
from godhand.tests.utils import get_couchdb_url


class ApiTest(unittest.TestCase):
    maxDiff = 5000
    root_email = 'root@domain.com'
    client_appname = 'my-client-appname'
    client_id = 'my-client-id'
    client_secret = 'my-client-secret'
    couchdb_url = get_couchdb_url()

    disable_auth = False

    def setUp(self):
        from godhand.rest import main
        self.api = TestApp(main(
            {},
            couchdb_url=self.couchdb_url,
            disable_auth=self.disable_auth,
            google_client_appname=self.client_appname,
            google_client_id=self.client_id,
            google_client_secret=self.client_secret,
            auth_secret='my-auth-secret',
            token_secret='my-token-secret',
            root_email=self.root_email,
        ))
        self.db = couchdb.client.Server(self.couchdb_url)['godhand']
        self.authdb = couchdb.client.Server(self.couchdb_url)['auth']
        self.addCleanup(self._cleanDb)

    @property
    def cli_env(self):
        return dict(
            os.environ,
            GODHAND_AUTH_SECRET='my-auth-secret',
            GODHAND_TOKEN_SECRET='my-token-secret',
            GODHAND_ROOT_EMAIL=self.root_email,
        )

    def use_fixture(self, fix):
        self.addCleanup(fix.cleanUp)
        fix.setUp()
        return fix

    def _cleanDb(self):
        client = couchdb.client.Server(self.couchdb_url)
        for dbname in ('godhand', 'auth'):
            try:
                client.delete(dbname)
            except couchdb.http.ResourceNotFound:
                pass

    def oauth2_login(self, email):
        response = self.api.get('/oauth2-init', params={
            'callback_url': 'http://success',
            'error_callback_url': 'http://error',
        }, status=302)
        url = urlparse(response.headers['location'])
        self.assertEquals(url.hostname, 'accounts.google.com')
        self.assertEquals(url.path, '/o/oauth2/v2/auth')
        query = parse_qs(url.query)
        self.assertEquals(
            query['redirect_uri'], ['http://localhost/oauth2-callback'])
        state = query['state'][0]
        assert state
        with mock.patch('godhand.rest.auth.client') as client:
            with mock.patch('godhand.rest.auth.requests') as requests:
                requests.post.return_value.status_code = 200
                requests.post.return_value.json.return_value = {
                    'id_token': 'myidtoken',
                }
                client.verify_id_token.return_value = {
                    'email_verified': True, 'email': email,
                }

                response = self.api.get(
                    '/oauth2-callback',
                    params={'state': state, 'code': 'mycode'},
                )
                assert response.headers['location'] == 'http://success'

                requests.post.assert_called_once_with(
                    'https://www.googleapis.com/oauth2/v4/token',
                    data={
                        'code': 'mycode',
                        'state': state,
                        'client_id': self.client_id,
                        'client_secret': self.client_secret,
                        'redirect_uri': 'http://localhost/oauth2-callback',
                        'grant_type': 'authorization_code',
                    },
                )


class UserLoggedInTest(ApiTest):
    user_id = 'write@company.com'

    def setUp(self):
        super(UserLoggedInTest, self).setUp()
        self.oauth2_login(self.user_id)


class SeriesTest(UserLoggedInTest):
    @property
    def example_series(self):
        return {
            'name': 'Berserk',
            'description': 'My Description',
            'genres': ['action', 'meme'],
            'author': 'My Author',
            'magazine': 'My Magazine',
            'number_of_volumes': 144,
        }


class SingleSeriesTest(SeriesTest):
    def setUp(self):
        super(SingleSeriesTest, self).setUp()
        response = self.api.post_json('/series', self.example_series).json_body
        self.series_id = response['id']

    @property
    def expected_series(self):
        return dict(self.example_series, id=self.series_id)

    @property
    def expected_series_full(self):
        return dict(self.expected_series, volumes=[], bookmarks=[])


class SingleVolumeTest(SingleSeriesTest):
    def setUp(self):
        super(SingleVolumeTest, self).setUp()
        with self.example_volume.packaged() as f:
            response = self.api.post(
                '/series/{}/volumes'.format(self.series_id),
                upload_files=[('volume', 'volume-007.cbt', f.read())],
                content_type='multipart/form-data',
            ).json_body
        self.user_series_id = response['series_id']
        self.volume_id = response['id']

    @property
    def example_volume(self):
        return CbtFile()

    @property
    def expected_volume(self):
        return {
            'id': self.volume_id,
            'filename': 'volume-007.cbt',
            'language': None,
            'volume_number': 7,
            'series_id': self.user_series_id,
            'next': None,
            'pages': [dict(
                x,
                url='http://localhost/volumes/{}/files/{}'.format(
                    self.volume_id, x['filename'])
            ) for x in self.example_volume.expected_pages],
        }

    @property
    def expected_volume_short(self):
        return {
            'id': self.volume_id,
            'filename': 'volume-007.cbt',
            'language': None,
            'volume_number': 7,
            'pages': len(self.example_volume.expected_pages),
        }

    @property
    def expected_user_series(self):
        return dict(
            self.expected_series,
            id=self.user_series_id,
        )

    @property
    def expected_user_series_full(self):
        return dict(
            self.expected_user_series,
            volumes=[self.expected_volume_short],
            bookmarks=[],
        )


class SeveralVolumesTest(SingleSeriesTest):
    n_volumes = 15

    def setUp(self):
        super(SeveralVolumesTest, self).setUp()
        self.volume_ids = []
        self.user_series_id = None
        for n_volume in range(self.n_volumes):
            with self.example_volume.packaged() as f:
                response = self.api.post(
                    '/series/{}/volumes'.format(self.series_id),
                    upload_files=[
                        ('volume', 'volume-{}.cbt'.format(n_volume), f.read()),
                    ],
                    content_type='multipart/form-data',
                ).json_body
            self.volume_ids.append(response['id'])
            if self.user_series_id:
                self.assertEquals(self.user_series_id, response['series_id'])
            else:
                self.user_series_id = response['series_id']
        self.assertIsNotNone(self.user_series_id)

    @property
    def example_volume(self):
        return CbtFile()

    def get_expected_volume(self, n_volume):
        volume_id = self.volume_ids[n_volume]
        return {
            'id': volume_id,
            'filename': 'volume-{}.cbt'.format(n_volume),
            'language': None,
            'volume_number': n_volume,
            'series_id': self.user_series_id,
            'pages': [dict(
                x,
                url='http://localhost/volumes/{}/files/{}'.format(
                    volume_id, x['filename'])
            ) for x in self.example_volume.expected_pages],
        }

    def get_expected_volume_short(self, n_volume):
        try:
            volume_id = self.volume_ids[n_volume]
        except IndexError:
            return None
        return {
            'id': volume_id,
            'filename': 'volume-{}.cbt'.format(n_volume),
            'language': None,
            'volume_number': n_volume,
            'pages': len(self.example_volume.expected_pages),
        }

    @property
    def expected_user_series(self):
        return dict(
            self.expected_series,
            id=self.user_series_id,
        )

    @property
    def expected_user_series_full(self):
        return dict(
            self.expected_user_series,
            volumes=[
                self.get_expected_volume_short(n)
                for n in range(self.n_volumes)
            ],
            bookmarks=[],
        )
