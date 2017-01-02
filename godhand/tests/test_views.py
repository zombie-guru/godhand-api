from urllib.parse import urlparse
from urllib.parse import parse_qs
import os
import unittest

from webtest import TestApp
import couchdb.client
import couchdb.http
import mock

from godhand.tests.fakevolumes import CbtFile
from godhand.tests.utils import get_couchdb_url


class ApiTest(unittest.TestCase):
    maxDiff = 5000
    root_email = 'root@domain.com'
    client_appname = 'my-client-appname'
    client_id = 'my-client-id'
    client_secret = 'my-client-secret'
    couchdb_url = get_couchdb_url()

    disable_auth = False

    def setUp(self):
        from godhand import main
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
        self.db = couchdb.client.Server(self.couchdb_url)['godhand']
        self.authdb = couchdb.client.Server(self.couchdb_url)['auth']
        self.addCleanup(self._cleanDb)

    @property
    def cli_env(self):
        return dict(
            os.environ,
            GODHAND_AUTH_SECRET='my-auth-secret',
            GODHAND_TOKEN_SECRET='my-token-secret',
            GODHAND_ROOT_EMAIL=self.root_email,
        )

    def use_fixture(self, fix):
        self.addCleanup(fix.cleanUp)
        fix.setUp()
        return fix

    def _cleanDb(self):
        client = couchdb.client.Server(self.couchdb_url)
        for dbname in ('godhand', 'auth'):
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


class TestLoggedOut(ApiTest):
    def test_get_account(self):
        expected = {
            'needs_authentication': True,
        }
        response = self.api.get('/account').json_body
        self.assertEquals(expected, response)

        self.oauth2_login('myemail@company.com')
        expected = {
            'needs_authentication': False,
            'subscribed_ids': [],
            'user_id': 'myemail@company.com',
            'usage': 0,
        }
        response = self.api.get('/account').json_body
        self.assertEquals(expected, response)

    def test_forbidden_views(self):
        self.api.get('/subscribers', status=403)
        self.api.get('/subscriptions', status=403)
        for action in ('allow', 'block', 'clear'):
            self.api.put_json('/subscribers', {
                'action': action,
                'user_id': 'another.dude@gmail.com',
            }, status=403)
            self.api.put_json('/subscriptions', {
                'action': action,
                'user_id': 'another.dude@gmail.com',
            }, status=403)


class UserLoggedInTest(ApiTest):
    user_id = 'write@company.com'

    def setUp(self):
        super(UserLoggedInTest, self).setUp()
        self.oauth2_login(self.user_id)

    @property
    def example_series(self):
        return {
            'name': 'Berserk',
            'description': 'My Description',
            'genres': ['action', 'meme'],
            'author': 'My Author',
            'magazine': 'My Magazine',
            'number_of_volumes': 144,
        }


class TestLoggedIn(UserLoggedInTest):
    def test_get_collection(self):
        expected = {'items': []}
        response = self.api.get('/series').json_body
        self.assertEquals(expected, response)
        # with q
        expected = {'items': []}
        response = self.api.get('/series', params={'name_q': 'a'}).json_body
        self.assertEquals(expected, response)

    def test_create_series(self):
        expected = self.example_series
        response = self.api.post_json('/series', self.example_series).json_body
        self.assertIsNotNone(response.pop('id'))
        self.assertEquals(expected, response)

    def test_upload_missing_series(self):
        self.api.post(
            '/series/missing/volumes',
            content_type='multipart/form-data',
            status=404,
        )

    def test_get_subscribers(self):
        self.assertEquals(
            {'items': []},
            self.api.get('/subscribers').json_body)
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


class SingleSeriesTest(UserLoggedInTest):
    def setUp(self):
        super(SingleSeriesTest, self).setUp()
        response = self.api.post_json('/series', self.example_series).json_body
        self.series_id = response['id']

    @property
    def expected_series(self):
        return dict(self.example_series, id=self.series_id)

    @property
    def expected_series_full(self):
        return dict(self.expected_series, volumes=[], bookmarks=[])


class TestSingleSeries(SingleSeriesTest):
    def test_get_collection(self):
        expected = {'items': [self.expected_series]}
        response = self.api.get('/series').json_body
        self.assertEquals(expected, response)
        # q positive match
        expected = {'items': [self.expected_series]}
        response = self.api.get('/series', params={'name_q': 'b'}).json_body
        self.assertEquals(expected, response)
        # q negative match
        expected = {'items': []}
        response = self.api.get('/series', params={'name_q': 'c'}).json_body
        self.assertEquals(expected, response)

    def test_get_series(self):
        expected = self.expected_series_full
        response = self.api.get('/series/{}'.format(self.series_id)).json_body
        self.assertEquals(expected, response)
        # no cover
        self.api.get('/series/{}/cover.jpg'.format(self.series_id), status=404)

    def test_upload_to_series(self):
        volume = CbtFile()
        with volume.packaged() as f:
            response = self.api.post(
                '/series/{}/volumes'.format(self.series_id),
                upload_files=[('volume', 'volume-007.cbt', f.read())],
                content_type='multipart/form-data',
            ).json_body

        self.assertIsNotNone(response.pop('id'))

        expected = '{}:{}'.format(
            self.series_id, self.user_id)
        self.assertEquals(expected, response.pop('series_id'))

        expected = {
            'filename': 'volume-007.cbt',
            'language': None,
            'volume_number': 7,
            'pages': volume.expected_pages,
        }
        self.assertEquals(expected, response)
        # no body
        self.api.post('/series/{}/volumes'.format(self.series_id), status=400)


class SingleVolumeTest(SingleSeriesTest):
    def setUp(self):
        super(SingleVolumeTest, self).setUp()
        with self.example_volume.packaged() as f:
            response = self.api.post(
                '/series/{}/volumes'.format(self.series_id),
                upload_files=[('volume', 'volume-007.cbt', f.read())],
                content_type='multipart/form-data',
            ).json_body
        self.user_series_id = response['series_id']
        self.volume_id = response['id']

    @property
    def example_volume(self):
        return CbtFile()

    @property
    def expected_volume(self):
        return {
            'id': self.volume_id,
            'filename': 'volume-007.cbt',
            'language': None,
            'volume_number': 7,
            'series_id': self.user_series_id,
            'next': None,
            'pages': [dict(
                x,
                url='http://localhost/volumes/{}/files/{}'.format(
                    self.volume_id, x['filename'])
            ) for x in self.example_volume.expected_pages],
        }

    @property
    def expected_volume_short(self):
        return {
            'id': self.volume_id,
            'filename': 'volume-007.cbt',
            'language': None,
            'volume_number': 7,
            'pages': len(self.example_volume.expected_pages),
        }

    @property
    def expected_user_series(self):
        return dict(
            self.expected_series,
            id=self.user_series_id,
        )

    @property
    def expected_user_series_full(self):
        return dict(
            self.expected_user_series,
            volumes=[self.expected_volume_short],
            bookmarks=[],
        )


class TestSingleVolume(SingleVolumeTest):
    def test_get_collection(self):
        expected = {'items': [self.expected_series]}
        response = self.api.get('/series').json_body
        self.assertEquals(expected, response)
        # collection positive
        expected = {'items': [self.expected_series]}
        response = self.api.get('/series', params={'name_q': 'b'}).json_body
        self.assertEquals(expected, response)
        # collection negative
        expected = {'items': []}
        response = self.api.get('/series', params={'name_q': 'c'}).json_body
        self.assertEquals(expected, response)
        # for user
        expected = {'items': [self.expected_user_series]}
        response = self.api.get(
            '/users/{}/series'.format(self.user_id),
        ).json_body
        self.assertEquals(expected, response)
        # forbidden
        self.api.get('/users/derp@herp.com/series', status=403)

    def test_get_series(self):
        expected = self.expected_series_full
        response = self.api.get('/series/{}'.format(self.series_id)).json_body
        self.assertEquals(expected, response)
        # user version
        expected = self.expected_user_series_full
        response = self.api.get(
            '/series/{}'.format(self.user_series_id)).json_body
        self.assertEquals(expected, response)
        self.api.get('/series/{}/cover.jpg'.format(self.user_series_id))
        # forbidden
        self.oauth2_login('derp@herp.com')
        self.api.get('/series/{}'.format(self.user_series_id), status=403)
        self.api.get(
            '/series/{}/cover.jpg'.format(self.user_series_id), status=403)

    def test_get_volume(self):
        expected = self.expected_volume
        response = self.api.get('/volumes/{}'.format(self.volume_id)).json_body
        self.assertEquals(expected, response)
        response = self.api.get('/volumes/{}/cover.jpg'.format(self.volume_id))
        self.assertEquals('image/jpeg', response.content_type)
        # forbidden
        self.oauth2_login('derp@herp.com')
        self.api.get('/volumes/{}'.format(self.volume_id), status=403)
        self.api.put_json('/volumes/{}'.format(self.volume_id), {
            'volume_number': 8,
        }, status=403)
        self.api.delete('/volumes/{}'.format(self.volume_id), status=403)
        self.api.get(
            '/volumes/{}/cover.jpg'.format(self.volume_id), status=403)

    def test_update_volume(self):
        self.api.put_json('/volumes/{}'.format(self.volume_id), {
            'volume_number': 8,
            'language': 'jpn',
        })
        expected = dict(self.expected_volume, volume_number=8, language='jpn')
        response = self.api.get('/volumes/{}'.format(self.volume_id)).json_body
        self.assertEquals(expected, response)

    def test_delete_last(self):
        """ Deleting the last volume of a series should delete the series.
        """
        self.api.delete('/volumes/{}'.format(self.volume_id))
        self.api.get('/volumes/{}'.format(self.volume_id), status=404)
        self.api.get('/series/{}'.format(self.user_series_id), status=404)
        expected = {'items': []}
        response = self.api.get(
            '/users/{}/series'.format(self.user_id)).json_body
        self.assertEquals(expected, response)

    def test_update_bookmark(self):
        for n_page in range(14):
            self.api.put_json(
                '/volumes/{}/bookmark'.format(self.volume_id),
                {'page_number': n_page},
            )
            page = self.example_volume.expected_pages[n_page]
            bookmarks = [{
                'page_number': n_page,
                'volume_id': self.volume_id,
                'series_id': self.user_series_id,
                'page0': 'http://localhost/volumes/{}/files/{}'.format(
                    self.volume_id, page['filename']),
                'page1': None,
                'number_of_pages': 15,
                'volume_number': 7,
            }]
            expected = dict(
                self.expected_user_series_full, bookmarks=bookmarks)
            response = self.api.get(
                '/series/{}'.format(self.user_series_id)).json_body
            for x in response['bookmarks']:
                self.assertIsNotNone(x.pop('last_updated'))
            self.assertEquals(expected, response)

            expected = {'items': bookmarks}
            response = self.api.get('/bookmarks').json_body
            for x in response['items']:
                self.assertIsNotNone(x.pop('last_updated'))
            self.assertEquals(expected, response)


class SeveralVolumesTest(SingleSeriesTest):
    n_volumes = 3

    def setUp(self):
        super(SeveralVolumesTest, self).setUp()
        self.volume_ids = []
        self.user_series_id = None
        for n_volume in range(self.n_volumes):
            with self.example_volume.packaged() as f:
                response = self.api.post(
                    '/series/{}/volumes'.format(self.series_id),
                    upload_files=[
                        ('volume', 'volume-{}.cbt'.format(n_volume), f.read()),
                    ],
                    content_type='multipart/form-data',
                ).json_body
            self.volume_ids.append(response['id'])
            if self.user_series_id:
                self.assertEquals(self.user_series_id, response['series_id'])
            else:
                self.user_series_id = response['series_id']
        self.assertIsNotNone(self.user_series_id)

    @property
    def example_volume(self):
        return CbtFile()

    def get_expected_volume(self, n_volume):
        volume_id = self.volume_ids[n_volume]
        return {
            'id': volume_id,
            'filename': 'volume-{}.cbt'.format(n_volume),
            'language': None,
            'volume_number': n_volume,
            'series_id': self.user_series_id,
            'pages': [dict(
                x,
                url='http://localhost/volumes/{}/files/{}'.format(
                    volume_id, x['filename'])
            ) for x in self.example_volume.expected_pages],
        }

    def get_expected_volume_short(self, n_volume):
        try:
            volume_id = self.volume_ids[n_volume]
        except IndexError:
            return None
        return {
            'id': volume_id,
            'filename': 'volume-{}.cbt'.format(n_volume),
            'language': None,
            'volume_number': n_volume,
            'pages': len(self.example_volume.expected_pages),
        }

    @property
    def expected_user_series(self):
        return dict(
            self.expected_series,
            id=self.user_series_id,
        )

    @property
    def expected_user_series_full(self):
        return dict(
            self.expected_user_series,
            volumes=[
                self.get_expected_volume_short(n)
                for n in range(self.n_volumes)
            ],
            bookmarks=[],
        )


class TestSeveralVolumes(SeveralVolumesTest):
    def test_get_user_series(self):
        expected = self.expected_user_series_full
        response = self.api.get(
            '/series/{}'.format(self.user_series_id)).json_body
        self.assertEquals(expected, response)

    def test_get_volume(self):
        for n_volume in range(self.n_volumes - 1):
            expected = dict(
                self.get_expected_volume(n_volume),
                next=self.get_expected_volume_short(n_volume + 1)
            )
            response = self.api.get(
                '/volumes/{}'.format(self.volume_ids[n_volume])).json_body
            self.assertEquals(expected, response)

        n_volume = self.n_volumes - 1
        expected = dict(self.get_expected_volume(n_volume), next=None)
        response = self.api.get(
            '/volumes/{}'.format(self.volume_ids[n_volume])).json_body
        self.assertEquals(expected, response)
        for volume_id in self.volume_ids:
            response = self.api.get('/volumes/{}/cover.jpg'.format(volume_id))
            self.assertEquals('image/jpeg', response.content_type)
        volume = self.get_expected_volume(0)
        self.assertTrue(len(volume['pages']) > 0)
        for page in volume['pages']:
            filename = page['filename']
            self.api.get('/volumes/{}/files/{}'.format(
                volume['id'], filename))
        # forbidden
        self.oauth2_login('derp@herp.com')
        volume = self.get_expected_volume(0)
        self.assertTrue(len(volume['pages']) > 0)
        for page in volume['pages']:
            filename = page['filename']
            self.api.get('/volumes/{}/files/{}'.format(
                volume['id'], filename), status=403)

    def test_delete(self):
        """ Deleting a single volume of a series should not delete the series.
        """
        volume_id = self.volume_ids[0]
        self.api.delete('/volumes/{}'.format(volume_id))
        self.api.get('/volumes/{}'.format(volume_id), status=404)
        expected = {'items': [self.expected_user_series]}
        response = self.api.get(
            '/users/{}/series'.format(self.user_id),
        ).json_body
        self.assertEquals(expected, response)

    def test_update_bookmark(self):
        volume_id = self.volume_ids[0]
        for n_page in range(14):
            self.api.put_json(
                '/volumes/{}/bookmark'.format(volume_id),
                {'page_number': n_page})
            page = self.example_volume.expected_pages[n_page]
            bookmarks = [{
                'page_number': n_page,
                'volume_id': volume_id,
                'series_id': self.user_series_id,
                'page0': 'http://localhost/volumes/{}/files/{}'.format(
                    volume_id, page['filename']),
                'page1': None,
                'number_of_pages': 15,
                'volume_number': 0,
            }]
            expected = dict(
                self.expected_user_series_full,
                bookmarks=bookmarks,
            )
            response = self.api.get(
                '/series/{}'.format(self.user_series_id)).json_body
            for x in response['bookmarks']:
                self.assertIsNotNone(x.pop('last_updated'))
            self.assertEquals(expected, response)

            expected = {'items': bookmarks}
            response = self.api.get('/bookmarks').json_body
            for x in response['items']:
                self.assertIsNotNone(x.pop('last_updated'))
            self.assertEquals(expected, response)

    def test_bookmark_ordering(self):
        """ Bookmarks should be ordered backwards in time.
        """
        page = self.example_volume.expected_pages[4]
        bookmarks = [{
            'page_number': 4,
            'volume_id': self.volume_ids[n_volume],
            'series_id': self.user_series_id,
            'number_of_pages': 15,
            'volume_number': n_volume,
            'page0': 'http://localhost/volumes/{}/files/{}'.format(
                self.volume_ids[n_volume], page['filename']),
            'page1': None,
        } for n_volume in range(self.n_volumes - 1, -1, -1)]

        for n_volume in range(self.n_volumes):
            volume_id = self.volume_ids[n_volume]
            self.api.put_json(
                '/volumes/{}/bookmark'.format(volume_id),
                {'page_number': 4})
        expected = dict(self.expected_user_series_full, bookmarks=bookmarks)
        response = self.api.get(
            '/series/{}'.format(self.user_series_id)).json_body
        for x in response['bookmarks']:
            self.assertIsNotNone(x.pop('last_updated'))
        self.assertEquals(expected, response)

        expected = {'items': bookmarks}
        response = self.api.get('/bookmarks').json_body
        for x in response['items']:
            self.assertIsNotNone(x.pop('last_updated'))
        self.assertEquals(expected, response)
