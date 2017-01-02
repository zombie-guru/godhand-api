from urllib.parse import urlparse
from urllib.parse import parse_qs
import unittest

from webtest import TestApp
import couchdb.client
import couchdb.http
import mock

from godhand.tests.utils import get_couchdb_url


class AuthApiTest(unittest.TestCase):
    maxDiff = 5000
    root_email = 'root@domain.com'
    client_appname = 'my-client-appname'
    client_id = 'my-client-id'
    client_secret = 'my-client-secret'
    couchdb_url = get_couchdb_url()

    disable_auth = False

    def setUp(self):
        from godhand.auth import main
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
        self.authdb = couchdb.client.Server(self.couchdb_url)['auth']
        self.addCleanup(self._cleanDb)

    def _cleanDb(self):
        client = couchdb.client.Server(self.couchdb_url)
        for dbname in ('auth',):
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
        with mock.patch('godhand.auth.views.client') as client:
            with mock.patch('godhand.auth.views.requests') as requests:
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


class TestLoggedOut(AuthApiTest):
    def test_success(self):
        self.oauth2_login('myemail@company.com')

    def test_bad_anti_forgery_token(self):
        with mock.patch('godhand.auth.views.client') as client:
            with mock.patch('godhand.auth.views.requests') as requests:
                requests.post.return_value.status_code = 200
                requests.post.return_value.json.return_value = {
                    'id_token': 'myidtoken',
                }
                client.verify_id_token.return_value = {
                    'email_verified': True, 'email': 'myemail@company.com',
                }

                self.api.get(
                    '/oauth2-callback',
                    params={'state': 'lolhacks', 'code': 'mycode'}, status=401,
                )

    def test_bad_code(self):
        with mock.patch('godhand.auth.views.requests') as requests:
            response = self.api.get(
                '/oauth2-init', params={
                    'callback_url': 'http://success',
                    'error_callback_url': 'http://error',
                }, status=302)
            url = urlparse(response.headers['location'])
            self.assertEquals(url.hostname, 'accounts.google.com')
            self.assertEquals(url.path, '/o/oauth2/v2/auth')
            query = parse_qs(url.query)
            state = query['state'][0]
            requests.post.return_value.status_code = 400
            response = self.api.get(
                '/oauth2-callback',
                params={'state': state, 'code': 'mycode'},
                status=303
            )
            assert response.headers['location'] == 'http://error'

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
