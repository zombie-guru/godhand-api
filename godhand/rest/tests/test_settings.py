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

        self.api.put_json('/settings')

        expected = {
            'user_id': self.user_id,
            'language': None,
        }
        response = self.api.get('/settings').json_body
        assert expected == response
