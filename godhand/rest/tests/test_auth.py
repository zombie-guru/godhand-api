import mock

from .utils import ApiTest
from .utils import RootLoggedInTest


class TestLoggedOut(ApiTest):
    def test_success(self):
        self.oauth2_login('myemail@company.com')

    def test_bad_anti_forgery_token(self):
        with mock.patch('godhand.rest.auth.client') as client:
            with mock.patch('godhand.rest.auth.requests') as requests:
                requests.post.return_value.status_code = 200
                requests.post.return_value.json.return_value = {
                    'id_token': 'myidtoken',
                }
                client.verify_id_token.return_value = {
                    'email_verified': True, 'email': 'myemail@company.com',
                }

                self.api.get(
                    '/oauth-callback',
                    params={'state': 'lolhacks', 'code': 'mycode'}, status=401,
                )

    def test_bad_code(self):
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

                requests.post.return_value.status_code = 400
                requests.post.return_value.json.return_value = {
                    'id_token': 'myidtoken',
                }
                client.verify_id_token.return_value = {
                    'email_verified': True, 'email': 'myemail@company.com',
                }

                self.api.get(
                    '/oauth-callback',
                    params={'state': state, 'code': 'mycode'},
                    status=401
                )

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


class TestNoUsers(RootLoggedInTest):
    def test_add_user(self):
        self.api.put('/users/user%40company.com')
        expected = {'email': 'user@company.com', 'groups': ['user']}
        response = self.api.get('/users/user%40company.com').json_body
        for key in ('_id', '_rev', '@class'):
            response.pop(key)
        self.assertEquals(expected, response)

    def test_delete(self):
        self.api.delete('/users/user%40company.com')


class TestSingleUser(RootLoggedInTest):
    def setUp(self):
        super(TestSingleUser, self).setUp()
        self.api.put('/users/user%40company.com')

    def test_update(self):
        self.api.put_json(
            '/users/user%40company.com', {'groups': ['user', 'admin']})
        expected = {
            'email': 'user@company.com',
            'groups': ['user', 'admin'],
        }
        response = self.api.get('/users/user%40company.com').json_body
        for key in ('_id', '_rev', '@class'):
            response.pop(key)
        self.assertEquals(expected, response)

    def test_delete(self):
        self.api.delete('/users/user%40company.com')
        self.api.get('/users/user%40company.com', status=404)
