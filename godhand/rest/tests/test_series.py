from godhand.tests.fakevolumes import CbtFile
from .utils import SeriesTest
from .utils import SingleSeriesTest
from .utils import SingleVolumeTest
from .utils import SeveralVolumesTest


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


class TestSingleVolume(SingleVolumeTest):
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


class TestSeveralVolumes(SeveralVolumesTest):
    def test_get_user_series(self):
        expected = self.expected_user_series_full
        response = self.api.get(
            '/series/{}'.format(self.user_series_id)).json_body
        self.assertEquals(expected, response)
