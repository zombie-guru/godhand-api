from godhand.tests.fakevolumes import CbtFile
from .utils import UserLoggedInTest


class SeriesTest(UserLoggedInTest):
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


class TestEmpty(SeriesTest):
    def test_get_collection(self):
        expected = {'items': []}
        response = self.api.get('/series').json_body
        self.assertEquals(expected, response)

    def test_get_collection_name_q(self):
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
            status=400,
        )


class SingleSeriesTest(SeriesTest):
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


class TestSingleSeriesTest(SingleSeriesTest):
    def test_get_collection(self):
        expected = {'items': [self.expected_series]}
        response = self.api.get('/series').json_body
        self.assertEquals(expected, response)

    def test_get_collection_name_q_positive(self):
        expected = {'items': [self.expected_series]}
        response = self.api.get('/series', params={'name_q': 'b'}).json_body
        self.assertEquals(expected, response)

    def test_get_collection_name_q_negative(self):
        expected = {'items': []}
        response = self.api.get('/series', params={'name_q': 'c'}).json_body
        self.assertEquals(expected, response)

    def test_get_series(self):
        expected = self.expected_series_full
        response = self.api.get('/series/{}'.format(self.series_id)).json_body
        self.assertEquals(expected, response)

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

    def test_upload_to_series_no_body(self):
        self.api.post(
            '/series/{}/volumes'.format(self.series_id),
            status=400,
        )


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
            'filename': 'volume-007.cbt',
            'language': None,
            'volume_number': 7,
            'pages': self.example_volume.expected_pages,
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

    def test_get_collection(self):
        expected = {'items': [self.expected_series]}
        response = self.api.get('/series').json_body
        self.assertEquals(expected, response)

    def test_get_collection_name_q_positive(self):
        expected = {'items': [self.expected_series]}
        response = self.api.get('/series', params={'name_q': 'b'}).json_body
        self.assertEquals(expected, response)

    def test_get_collection_name_q_negative(self):
        expected = {'items': []}
        response = self.api.get('/series', params={'name_q': 'c'}).json_body
        self.assertEquals(expected, response)

    def test_get_user_collection(self):
        expected = {'items': [self.expected_user_series]}
        response = self.api.get(
            '/users/{}/series'.format(self.user_id),
        ).json_body
        self.assertEquals(expected, response)

    def test_get_user_collection_forbidden(self):
        self.api.get('/users/derp@herp.com/series', status=403)

    def test_get_series(self):
        expected = self.expected_series_full
        response = self.api.get('/series/{}'.format(self.series_id)).json_body
        self.assertEquals(expected, response)

    def test_get_user_series(self):
        expected = self.expected_user_series_full
        response = self.api.get(
            '/series/{}'.format(self.user_series_id)).json_body
        self.assertEquals(expected, response)

    def test_get_series_forbidden(self):
        self.oauth2_login('derp@herp.com')
        self.api.get('/series/{}'.format(self.user_series_id), status=403)

    def test_update_bookmark(self):
        for n_page in range(14):
            self.api.put_json(
                '/volumes/{}/bookmark'.format(self.volume_id),
                {'page_number': n_page},
            )
            expected = dict(
                self.expected_user_series_full,
                bookmarks=[{
                    'page_number': n_page,
                    'volume_id': self.volume_id,
                    'series_id': self.user_series_id,
                    'max_spread': 1,
                    'number_of_pages': 15,
                    'volume_number': 7,
                }],
            )
            response = self.api.get(
                '/series/{}'.format(self.user_series_id)).json_body
            for x in response['bookmarks']:
                self.assertIsNotNone(x.pop('last_updated'))
            self.assertEquals(expected, response)
