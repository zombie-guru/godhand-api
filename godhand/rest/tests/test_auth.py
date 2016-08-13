from .utils import ApiTest


class TestLoggedOut(ApiTest):
    def test_success(self):
        requests = self.mocks['godhand.rest.auth.requests']
        client = self.mocks['godhand.rest.auth.client']

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
            'email_verified': True, 'email': 'myemail@company.com',
        }

        expected = {'email': 'myemail@company.com'}
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

    def test_bad_anti_forgery_token(self):
        requests = self.mocks['godhand.rest.auth.requests']
        client = self.mocks['godhand.rest.auth.client']

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
        requests = self.mocks['godhand.rest.auth.requests']
        client = self.mocks['godhand.rest.auth.client']

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
