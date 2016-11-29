import mock
from urllib.parse import urlparse
from urllib.parse import parse_qs

from .utils import ApiTest


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
                    '/oauth2-callback',
                    params={'state': 'lolhacks', 'code': 'mycode'}, status=401,
                )

    def test_bad_code(self):
        with mock.patch('godhand.rest.auth.requests') as requests:
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
