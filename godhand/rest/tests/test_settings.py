from .utils import WriteUserLoggedInTest


class TestSettings(WriteUserLoggedInTest):
    def test_get_default(self):
        expected = {
            'user_id': self.user_id,
            'language': None,
        }
        response = self.api.get('/settings').json_body
        assert expected == response

    def test_update(self):
        self.api.put_json('/settings', {'language': 'jpn'})

        expected = {
            'user_id': self.user_id,
            'language': 'jpn',
        }
        response = self.api.get('/settings').json_body
        assert expected == response

        expected = {
            'needs_authentication': False,
            'permissions': {
                'view': True,
                'write': True,
                'admin': True,
            },
            'user_id': self.user_id,
            'language': 'jpn',
        }
        response = self.api.get('/user').json_body
        assert expected == response

        self.api.put_json('/settings')

        expected = {
            'user_id': self.user_id,
            'language': None,
        }
        response = self.api.get('/settings').json_body
        assert expected == response

        expected = {
            'needs_authentication': False,
            'permissions': {
                'view': True,
                'write': True,
                'admin': True,
            },
            'user_id': self.user_id,
            'language': None,
        }
        response = self.api.get('/user').json_body
        assert expected == response

    def test_get_set_subscribers(self):
        expected = {'items': []}
        response = self.api.get('/account/subscribers').json_body
        assert expected == response

        self.api.put('/account/subscribers/derp@herp.com')

        expected = {'items': ['derp@herp.com']}
        response = self.api.get('/account/subscribers').json_body
        assert expected == response
