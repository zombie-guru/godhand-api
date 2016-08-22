from io import BytesIO
import os

from PIL import Image

from .utils import CbtFile
from .utils import CbzFile
from .utils import WriteUserLoggedInTest
from .utils import tmp_cbt


class TestEmpty(WriteUserLoggedInTest):
    def test_get_missing(self):
        self.api.get('/series/missing', status=404)

    def test_upload_missing_series(self):
        with tmp_cbt(['page{:x}.jpg'.format(x) for x in range(15)]) as f:
            self.api.post(
                '/series/missing/volumes',
                upload_files=[('input', 'volume-007.cbt', f.read())],
                content_type='multipart/form-data',
                status=404
            )

    def test_update_progress_missing(self):
        self.api.put_json(
            '/series/missing/reader-progress',
            {'volume_number': 432, 'page_number': 7}, status=404)

    def test_get_progress_missing(self):
        self.api.get('/series/missing/reader-progress', status=404)

    def test_create_series(self):
        response = self.api.post_json(
            '/series', {
                'name': 'Berserk',
                'description': 'My Description',
                'genres': ['action', 'meme'],
                'dbpedia_uri': None,
                'author': None,
                'magazine': None,
                'number_of_volumes': None,
            }
        ).json_body
        self.assertEquals(len(response['series']), 1)
        series_id = response['series'][0]
        # Get the series by the key
        expected = {
            '@class': 'Series',
            '_id': series_id,
            'name': 'Berserk',
            'description': 'My Description',
            'genres': ['action', 'meme'],
            'volumes': [],
            'author': None,
            'magazine': None,
            'number_of_volumes': None,
        }
        response = self.api.get('/series/{}'.format(series_id)).json_body
        assert response.pop('_rev')
        self.assertEquals(expected, response)


class SingleSeriesTest(WriteUserLoggedInTest):
    def setUp(self):
        super(SingleSeriesTest, self).setUp()
        response = self.api.post_json(
            '/series', {
                'name': 'Berserk',
                'description': 'My Description',
                'genres': ['action', 'meme'],
                'dbpedia_uri': None,
                'author': None,
                'magazine': None,
                'number_of_volumes': None,
            }
        ).json_body
        self.assertEquals(len(response['series']), 1)
        self.series_id = response['series'][0]

    @property
    def expected_series(self):
        return {
            '@class': 'Series',
            '_id': self.series_id,
            'name': 'Berserk',
            'description': 'My Description',
            'genres': ['action', 'meme'],
            'volumes': [],
            'author': None,
            'magazine': None,
            'number_of_volumes': None,
        }


class TestSingleSeries(SingleSeriesTest):
    def test_get_collection(self):
        expected = {'items': []}
        response = self.api.get('/series').json_body
        for x in response['items']:
            x.pop('_rev')
        self.assertEquals(expected, response)

    def test_get_collection_by_genre_all(self):
        expected = {'items': [self.expected_series]}
        response = self.api.get(
            '/series', params={'genre': 'meme', 'include_empty': True},
        ).json_body
        for x in response['items']:
            x.pop('_rev')
        self.assertEquals(expected, response)

    def test_get_collection_by_name_all(self):
        expected = {'items': [self.expected_series]}
        response = self.api.get(
            '/series', params={'name': 'Berserk', 'include_empty': True},
        ).json_body
        for x in response['items']:
            x.pop('_rev')
        self.assertEquals(expected, response)

    def test_add_volume_to_series(self):
        for cls in (CbtFile, CbzFile):
            cbt = cls()
            with cbt.packaged() as f:
                response = self.api.post(
                    '/series/{}/volumes'.format(self.series_id),
                    upload_files=[('input', 'volume-007' + cls.ext, f.read())],
                    content_type='multipart/form-data',
                ).json_body
            self.assertEquals(len(response['volumes']), 1)
            volume_id = response['volumes'][0]
            expected = {
                '@class': 'Volume',
                '_id': volume_id,
                'volume_number': 7,
                'filename': 'volume-007' + cls.ext,
                'series_id': self.series_id,
            }
            response = self.api.get('/volumes/{}'.format(volume_id)).json_body
            response.pop('_rev')
            pages = response.pop('pages')
            self.assertEquals(expected, response)
            # validate pages
            urls = [x.pop('url') for x in pages]
            self.assertEquals(
                ['page-{:x}.png'.format(x) for x in range(15)],
                [os.path.basename(x) for x in urls])
            for n_url, url in enumerate(urls):
                cbt_page = cbt.pages[n_url]
                im = Image.open(BytesIO(self.api.get(url).body))
                self.assertEquals(
                    (0x00, 0x00, 0x00), im.getpixel((1, 0)))
                self.assertEquals(
                    (0xfe, 0xfe, 0xfe), im.getpixel(cbt_page['black_pixel']))
            expected = [{
                'width': page['width'],
                'height': page['height'],
                'orientation': page['orientation'],
            } for page in cbt.pages]
            for key in ('path',):
                for page in pages:
                    page.pop(key)
            self.assertEquals(expected, pages)

    def test_get_and_store_series_progress(self):
        expected = {'volume_number': 0, 'page_number': 0}
        response = self.api.get(
            '/series/{}/reader-progress'.format(self.series_id)).json_body
        for key in ('_id', '_rev', '@class'):
            response.pop(key, None)
        self.assertEquals(expected, response)

        self.api.put_json(
            '/series/{}/reader-progress'.format(self.series_id),
            {'volume_number': 432, 'page_number': 7})

        expected = {'volume_number': 432, 'page_number': 7}
        response = self.api.get(
            '/series/{}/reader-progress'.format(self.series_id)).json_body
        for key in ('_id', '_rev', '@class'):
            response.pop(key, None)
        self.assertEquals(expected, response)


class SingleVolumeInSeriesTest(SingleSeriesTest):
    def setUp(self):
        super(SingleVolumeInSeriesTest, self).setUp()
        with tmp_cbt(['page{:x}.jpg'.format(x) for x in range(15)]) as f:
            response = self.api.post(
                '/series/{}/volumes'.format(self.series_id),
                upload_files=[('input', 'volume-007.cbt', f.read())],
                content_type='multipart/form-data',
            ).json_body
        self.assertEquals(len(response['volumes']), 1)
        self.volume_id = response['volumes'][0]

    @property
    def expected_series(self):
        return {
            '@class': 'Series',
            '_id': self.series_id,
            'name': 'Berserk',
            'description': 'My Description',
            'genres': ['action', 'meme'],
            'volumes': [
                {
                    'id': self.volume_id,
                    'volume_number': 7,
                }
            ],
            'author': None,
            'magazine': None,
            'number_of_volumes': None,
        }


class TestSingleVolumeInSeries(SingleVolumeInSeriesTest):
    def test_get_series_by_id(self):
        response = self.api.get('/series/{}'.format(self.series_id)).json_body
        assert response.pop('_rev')
        self.assertEquals(self.expected_series, response)

    def test_get_collection(self):
        expected = {'items': [self.expected_series]}
        response = self.api.get('/series').json_body
        for x in response['items']:
            x.pop('_rev')
        self.assertEquals(expected, response)

    def test_get_collection_by_genre(self):
        expected = {'items': [self.expected_series]}
        response = self.api.get('/series', params={'genre': 'meme'}).json_body
        for x in response['items']:
            x.pop('_rev')
        self.assertEquals(expected, response)

    def test_get_collection_by_genre_partial(self):
        expected = {'items': [self.expected_series]}
        response = self.api.get('/series', params={'genre': 'ME'}).json_body
        for x in response['items']:
            x.pop('_rev')
        self.assertEquals(expected, response)

    def test_get_collection_by_genre_negative(self):
        expected = {'items': []}
        response = self.api.get(
            '/series', params={'genre': 'romance'}).json_body
        for x in response['items']:
            x.pop('_rev')
        self.assertEquals(expected, response)

    def test_get_collection_by_name(self):
        expected = {'items': [self.expected_series]}
        response = self.api.get('/series', params={
            'name': 'berserk',
            'full_match': 'true',
        }).json_body
        for x in response['items']:
            x.pop('_rev')
        self.assertEquals(expected, response)

    def test_get_collection_by_name_partial(self):
        expected = {'items': [self.expected_series]}
        response = self.api.get(
            '/series', params={'name': 'be'}).json_body
        for x in response['items']:
            x.pop('_rev')
        self.assertEquals(expected, response)

    def test_get_collection_by_name_negative(self):
        expected = {'items': []}
        response = self.api.get('/series', params={'name': 'derp'}).json_body
        self.assertEquals(expected, response)

    def test_get_volume_by_index(self):
        expected = {
            '@class': 'Volume',
            '_id': self.volume_id,
            'filename': 'volume-007.cbt',
            'series_id': self.series_id,
            'volume_number': 7,
        }
        response = self.api.get(
            '/series/{}/volumes/0'.format(self.series_id)).json_body
        for key in ('_rev', 'pages'):
            response.pop(key)
        self.assertEquals(expected, response)

    def test_get_volume_by_index_missing(self):
        self.api.get(
            '/series/{}/volumes/1'.format(self.series_id), status=404)

    def test_get_image_by_page_number(self):
        expected = {
            'height': 128,
            'width': 128,
            'orientation': 'horizontal',
        }
        response = self.api.get(
            '/volumes/{}/pages/0'.format(self.volume_id)).json_body
        self.assertEquals('page0.jpg', os.path.basename(response.pop('url')))
        self.assertEquals(expected, response)

    def test_get_image_by_page_number_missing(self):
        self.api.get(
            '/volumes/{}/pages/10000'.format(self.volume_id), status=404)
