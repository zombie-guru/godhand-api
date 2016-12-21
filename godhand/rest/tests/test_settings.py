from .utils import UserLoggedInTest


class TestSettings(UserLoggedInTest):
    def test_get_set_subscribers(self):
        expected = {'items': []}
        response = self.api.get('/account/subscribers').json_body
        assert expected == response

        self.api.put('/account/subscribers/derp@herp.com')

        expected = {'items': ['derp@herp.com']}
        response = self.api.get('/account/subscribers').json_body
        assert expected == response

        self.oauth2_login('derp@herp.com')

        expected = {'items': []}
        response = self.api.get('/account/subscribers').json_body
        assert expected == response
