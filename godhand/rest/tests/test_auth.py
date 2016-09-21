import mock
from urllib.parse import urlparse
from urllib.parse import parse_qs

from .utils import ApiTest
from .utils import RootLoggedInTest
from .utils import tmp_cbt


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

    def test_get_permissions(self):
        self.api.get('/permissions', status=401)


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

    def test_get_permissions(self):
        expected = {
            'view': True,
            'write': True,
            'admin': True,
        }
        response = self.api.get('/permissions').json_body
        assert expected == response


class TestSingleUser(RootLoggedInTest):
    def setUp(self):
        super(TestSingleUser, self).setUp()
        self.api.put('/users/user%40company.com')

    def test_get_users(self):
        expected = {'items': [
            {
                '@class': 'User',
                '_id': 'user:root@domain.com',
                'email': 'root@domain.com',
                'groups': ['root']
            },
            {
                '@class': 'User',
                '_id': 'user:user@company.com',
                'email': 'user@company.com',
                'groups': [
                    'user',
                ]
            },
        ]}
        response = self.api.get('/users').json_body
        for key in ('_rev',):
            for x in response['items']:
                x.pop(key)
        self.assertEquals(expected, response)

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


class TestSingleUserLoggedIn(RootLoggedInTest):
    def setUp(self):
        super(TestSingleUserLoggedIn, self).setUp()
        self.api.put('/users/user%40company.com')
        self.api.post('/logout')
        self.oauth2_login('user@company.com')

    def test_admin_only_views(self):
        self.api.get('/users', status=403)
        self.api.put_json(
            '/users/user%40company.com', {'groups': ['admin']}, status=403)
        self.api.get('/users/user%40company.com', status=403)

    def test_write_only_views(self):
        self.api.post_json(
            '/series', {
                'name': 'Berserk',
                'description': 'My Description',
                'genres': ['action', 'meme'],
                'dbpedia_uri': None,
                'author': None,
                'magazine': None,
                'number_of_volumes': None,
            }, status=403)
        with tmp_cbt(['page{:x}.jpg'.format(x) for x in range(15)]) as f:
            self.api.post(
                '/series/missing/volumes',
                upload_files=[('input', 'volume-007.cbt', f.read())],
                content_type='multipart/form-data',
                status=403
            )

    def test_permission_tests(self):
        self.api.get('/permissions/view/test')
        self.api.get('/permissions/write/test', status=403)


class TestAuthDisabled(ApiTest):
    disable_auth = True

    def test_admin_only_views(self):
        self.api.put_json('/users/user%40company.com', {'groups': ['admin']})
        self.api.get('/users/user%40company.com')

    def test_write_only_views(self):
        self.api.post_json(
            '/series', {
                'name': 'Berserk',
                'description': 'My Description',
                'genres': ['action', 'meme'],
                'dbpedia_uri': None,
                'author': None,
                'magazine': None,
                'number_of_volumes': None,
            })
        with tmp_cbt(['page{:x}.jpg'.format(x) for x in range(15)]) as f:
            self.api.post(
                '/series/missing/volumes',
                upload_files=[('input', 'volume-007.cbt', f.read())],
                content_type='multipart/form-data',
                status=400
            )

    def test_permission_tests(self):
        self.api.get('/permissions/view/test')
        self.api.get('/permissions/write/test')
