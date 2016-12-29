from .utils import ApiTest
from .utils import UserLoggedInTest


class TestForbidden(ApiTest):
    def test_get_subscribers(self):
        self.api.get('/subscribers', status=403)

    def test_update_subscribers(self):
        for action in ('allow', 'block', 'clear'):
            self.api.put_json('/subscribers', {
                'action': action,
                'user_id': 'another.dude@gmail.com',
            }, status=403)

    def test_get_subscriptions(self):
        self.api.get('/subscriptions', status=403)

    def test_update_subscriptions(self):
        for action in ('allow', 'block', 'clear'):
            self.api.put_json('/subscriptions', {
                'action': action,
                'user_id': 'another.dude@gmail.com',
            }, status=403)


class TestLoggedIn(UserLoggedInTest):
    def test_get_subscribers(self):
        self.assertEquals(
            {'items': []},
            self.api.get('/subscribers').json_body)

    def test_get_subscriptions(self):
        self.assertEquals(
            {'items': []},
            self.api.get('/subscriptions').json_body)

    def test_valid_subscription(self):
        subscriber = 'other@gmail.com'

        self.api.put_json('/subscribers', {
            'action': 'allow',
            'user_id': subscriber,
        })

        self.oauth2_login(subscriber)
        self.api.put_json('/subscriptions', {
            'action': 'allow',
            'user_id': self.user_id,
        })

        expected = {'items': [{
            'id': 'subscription:{}:{}'.format(self.user_id, subscriber),
            'publisher_id': self.user_id,
            'subscriber_id': subscriber,
        }]}

        self.oauth2_login(self.user_id)
        self.assertEquals(expected, self.api.get('/subscribers').json_body)

        self.oauth2_login('other@gmail.com')
        self.assertEquals(expected, self.api.get('/subscriptions').json_body)

    def test_only_subscriber(self):
        self.api.put_json('/subscriptions', {
            'action': 'allow',
            'user_id': 'other@gmail.com',
        })
        self.assertEquals(
            {'items': []},
            self.api.get('/subscriptions').json_body)

        self.oauth2_login('other@gmail.com')
        self.assertEquals(
            {'items': []},
            self.api.get('/subscribers').json_body)

    def test_only_publisher(self):
        self.api.put_json('/subscribers', {
            'action': 'allow',
            'user_id': 'other@gmail.com',
        })
        self.assertEquals(
            {'items': []},
            self.api.get('/subscribers').json_body)

        self.oauth2_login('other@gmail.com')
        self.assertEquals(
            {'items': []},
            self.api.get('/subscriptions').json_body)
