from .utils import ApiTest


class TestAccount(ApiTest):
    def test_logged_out(self):
        expected = {
            'needs_authentication': True,
        }
        response = self.api.get('/account').json_body
        self.assertEquals(expected, response)

    def test_logged_in(self):
        self.oauth2_login('myemail@company.com')
        expected = {
            'needs_authentication': False,
            'subscribed_ids': [],
            'user_id': 'myemail@company.com',
            'usage': 0,
        }
        response = self.api.get('/account').json_body
        self.assertEquals(expected, response)

    # def test_get_set_subscribers(self):
    #     self.oauth2_login('myemail@company.com')
    #     expected = {'items': []}
    #     response = self.api.get('/account/subscribers').json_body
    #     self.assertEquals(expected, response)
    #
    #     self.api.put('/account/subscribers/derp@herp.com')
    #
    #     expected = {'items': ['derp@herp.com']}
    #     response = self.api.get('/account/subscribers').json_body
    #     self.assertEquals(expected, response)
    #
    #     self.oauth2_login('derp@herp.com')
    #
    #     expected = {'items': []}
    #     response = self.api.get('/account/subscribers').json_body
    #     self.assertEquals(expected, response)
    #
    #     expected = {
    #         'needs_authentication': False,
    #         'subscribed_ids': ['myemail@company.com'],
    #         'user_id': 'derp@herp.com',
    #         'usage': 0,
    #     }
    #     response = self.api.get('/account').json_body
    #     self.assertEquals(expected, response)
    #
    #     self.oauth2_login('myemail@company.com')
    #     self.api.delete('/account/subscribers/derp@herp.com')
    #     expected = {'items': []}
    #     response = self.api.get('/account/subscribers').json_body
    #     self.assertEquals(expected, response)
    #
    #     self.oauth2_login('derp@herp.com')
    #     expected = {
    #         'needs_authentication': False,
    #         'subscribed_ids': [],
    #         'user_id': 'derp@herp.com',
    #         'usage': 0,
    #     }
    #     response = self.api.get('/account').json_body
    #     self.assertEquals(expected, response)
