from io import BytesIO
import os

from PIL import Image

from godhand.tests.fakevolumes import CbtFile
from godhand.tests.fakevolumes import CbzFile
from .utils import WriteUserLoggedInTest
from .utils import tmp_cbt


class TestEmpty(WriteUserLoggedInTest):
    def test_get_missing(self):
        self.api.get('/series/missing', status=400)

    def test_upload_missing_series(self):
        with tmp_cbt(['page{:x}.jpg'.format(x) for x in range(15)]) as f:
            self.api.post(
                '/series/missing/volumes',
                upload_files=[('input', 'volume-007.cbt', f.read())],
                content_type='multipart/form-data',
                status=400
            )

    def test_update_progress_missing(self):
        self.api.put_json(
            '/volumes/missing/reader_progress',
            {'page_number': 7}, status=400)

    def test_get_progress_missing(self):
        self.api.get('/series/missing/reader_progress', status=400)

    def test_get_overall_progress(self):
        expected = {'items': []}
        response = self.api.get('/reader_progress').json_body
        assert expected == response

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
            'id': series_id,
            'name': 'Berserk',
            'description': 'My Description',
            'genres': ['action', 'meme'],
            'author': None,
            'cover_page': {
                'page_number': None,
                'volume_id': None,
            },
            'magazine': None,
            'number_of_volumes': None,
            'volumes': [],
        }
        response = self.api.get('/series/{}'.format(series_id)).json_body
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
            'id': self.series_id,
            'name': 'Berserk',
            'description': 'My Description',
            'genres': ['action', 'meme'],
            'author': None,
            'cover_page': {
                'page_number': None,
                'volume_id': None,
            },
            'magazine': None,
            'number_of_volumes': None,
        }


class TestSingleSeries(SingleSeriesTest):
    def test_get_collection(self):
        expected = {'items': []}
        response = self.api.get('/series').json_body
        self.assertEquals(expected, response)

    def test_get_collection_by_genre_all(self):
        expected = {'items': [self.expected_series]}
        response = self.api.get(
            '/series', params={'genre': 'meme', 'include_empty': True},
        ).json_body
        self.assertEquals(expected, response)

    def test_get_collection_by_name_all(self):
        expected = {'items': [self.expected_series]}
        response = self.api.get(
            '/series', params={'name': 'Berserk', 'include_empty': True},
        ).json_body
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
                'id': volume_id,
                'volume_number': 7,
                'language': None,
                'filename': 'volume-007' + cls.ext,
                'series_id': self.series_id,
            }
            response = self.api.get('/volumes/{}'.format(volume_id)).json_body
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
            for key in ('filename',):
                for page in pages:
                    page.pop(key)
            self.assertEquals(expected, pages)


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
            'id': self.series_id,
            'name': 'Berserk',
            'description': 'My Description',
            'genres': ['action', 'meme'],
            'author': None,
            'cover_page': {
                'page_number': None,
                'volume_id': None,
            },
            'magazine': None,
            'number_of_volumes': None,
        }

    @property
    def expected_series_full(self):
        return dict(self.expected_series, volumes=self.expected_volumes)

    @property
    def expected_volumes(self):
        return [{
            'id': self.volume_id,
            'filename': 'volume-007.cbt',
            'volume_number': 7,
            'language': None,
            'pages': 15,
            'progress': None,
        }]


class TestSingleVolumeInSeries(SingleVolumeInSeriesTest):
    def test_get_series_by_id(self):
        expected = self.expected_series_full
        response = self.api.get('/series/{}'.format(self.series_id)).json_body
        self.assertEquals(expected, response)

        expected = self.expected_series_full
        expected['volumes'] = []
        response = self.api.get(
            '/series/{}'.format(self.series_id),
            params={'language': 'eng'}).json_body
        self.assertEquals(expected, response)

    def test_get_series_volumes(self):
        expected = {
            'volumes': self.expected_series_full['volumes'],
        }
        response = self.api.get(
            '/series/{}/volumes'.format(self.series_id)).json_body
        self.assertEquals(expected, response)

    def test_get_collection(self):
        expected = {'items': [self.expected_series]}
        response = self.api.get('/series').json_body
        self.assertEquals(expected, response)

    def test_get_collection_by_genre(self):
        expected = {'items': [self.expected_series]}
        response = self.api.get('/series', params={'genre': 'meme'}).json_body
        self.assertEquals(expected, response)

    def test_get_collection_by_genre_partial(self):
        expected = {'items': [self.expected_series]}
        response = self.api.get('/series', params={'genre': 'ME'}).json_body
        self.assertEquals(expected, response)

    def test_get_collection_by_genre_negative(self):
        expected = {'items': []}
        response = self.api.get(
            '/series', params={'genre': 'romance'}).json_body
        self.assertEquals(expected, response)

    def test_get_collection_by_name(self):
        expected = {'items': [self.expected_series]}
        response = self.api.get('/series', params={
            'name': 'berserk',
            'full_match': 'true',
        }).json_body
        self.assertEquals(expected, response)

    def test_get_collection_by_name_partial(self):
        expected = {'items': [self.expected_series]}
        response = self.api.get(
            '/series', params={'name': 'be'}).json_body
        self.assertEquals(expected, response)

    def test_get_collection_by_name_negative(self):
        expected = {'items': []}
        response = self.api.get('/series', params={'name': 'derp'}).json_body
        self.assertEquals(expected, response)

    def test_update_volume_language(self):
        self.api.put_json('/volumes/{}'.format(self.volume_id), {
            'language': 'eng',
        })
        response = self.api.get('/volumes/{}'.format(self.volume_id)).json_body
        self.assertEquals(response['language'], 'eng')
        self.assertEquals(response['volume_number'], 7)
        self.assertEquals(response['series_id'], self.series_id)

        expected = self.expected_series_full
        expected['volumes'][0]['language'] = 'eng'
        response = self.api.get('/series/{}'.format(self.series_id)).json_body
        self.assertEquals(expected, response)

        response = self.api.get(
            '/series/{}'.format(self.series_id),
            params={'language': 'eng'}).json_body
        self.assertEquals(expected, response)

        response = self.api.get(
            '/series/{}'.format(self.series_id),
            params={'language': 'eng'}).json_body
        self.assertEquals(expected, response)

        expected = self.expected_series_full
        expected['volumes'] = []
        response = self.api.get(
            '/series/{}'.format(self.series_id),
            params={'language': 'jpn'}).json_body
        self.assertEquals(expected, response)

        expected = {'items': [self.expected_series]}
        response = self.api.get(
            '/series',
            params={'language': 'eng'},
        ).json_body
        self.assertEquals(expected, response)
        response = self.api.get(
            '/series',
        ).json_body
        self.assertEquals(expected, response)

        expected = {'items': []}
        response = self.api.get(
            '/series',
            params={'language': 'jpn'},
        ).json_body
        self.assertEquals(expected, response)

        self.api.put_json('/volumes/{}'.format(self.volume_id), {
            'language': 'jpn',
        })

        expected = {'items': [self.expected_series]}
        response = self.api.get(
            '/series',
            params={'language': 'jpn'},
        ).json_body
        self.assertEquals(expected, response)
        response = self.api.get(
            '/series',
        ).json_body
        self.assertEquals(expected, response)

        expected = {'items': []}
        response = self.api.get(
            '/series',
            params={'language': 'eng'},
        ).json_body
        self.assertEquals(expected, response)

    def test_update_volume_number(self):
        self.api.put_json('/volumes/{}'.format(self.volume_id), {
            'volume_number': 10,
        })
        response = self.api.get('/volumes/{}'.format(self.volume_id)).json_body
        self.assertEquals(response['language'], None)
        self.assertEquals(response['volume_number'], 10)
        self.assertEquals(response['series_id'], self.series_id)

    def test_update_series_invalid(self):
        self.api.put_json('/volumes/{}'.format(self.volume_id), {
            'series_id': 'derp',
        })
        response = self.api.get('/volumes/{}'.format(self.volume_id)).json_body
        self.assertEquals(response['language'], None)
        self.assertEquals(response['volume_number'], 7)
        self.assertEquals(response['series_id'], self.series_id)

    def test_update_series_same(self):
        self.api.put_json('/volumes/{}'.format(self.volume_id), {
            'series_id': self.series_id,
        })
        response = self.api.get('/volumes/{}'.format(self.volume_id)).json_body
        self.assertEquals(response['language'], None)
        self.assertEquals(response['volume_number'], 7)
        self.assertEquals(response['series_id'], self.series_id)

    def test_get_volume_by_index(self):
        expected = {
            'id': self.volume_id,
            'filename': 'volume-007.cbt',
            'series_id': self.series_id,
            'language': None,
            'volume_number': 7,
        }
        response = self.api.get(
            '/series/{}/volumes/0'.format(self.series_id)).json_body
        for key in ('pages',):
            response.pop(key)
        self.assertEquals(expected, response)

    def test_get_volume_by_index_missing(self):
        self.api.get(
            '/series/{}/volumes/1'.format(self.series_id), status=404)

    def test_get_series_cover(self):
        response = self.api.get('/series/{}/cover.jpg'.format(self.series_id))
        self.assertEquals(response.content_type, 'image/jpeg')

    def test_get_image_by_page_number_as_image(self):
        response = self.api.get('/volumes/{}/pages/0'.format(self.volume_id))
        self.assertEquals(response.content_type, 'image/jpeg')
        response = self.api.get(
            '/series/{}/volumes/0/pages/0'.format(self.series_id))
        self.assertEquals(response.content_type, 'image/jpeg')

    def test_get_image_by_page_number_missing(self):
        self.api.get(
            '/volumes/{}/pages/10000'.format(self.volume_id), status=404)
        self.api.get(
            '/series/{}/volumes/0/pages/10000'.format(self.series_id),
            status=404)

    def test_get_and_store_series_progress(self):
        expected = {'items': []}
        response = self.api.get(
            '/series/{}/reader_progress'.format(self.series_id)).json_body
        self.assertEquals(expected, response)

        for n_page in range(10):
            self.api.put_json(
                '/volumes/{}/reader_progress'.format(self.volume_id),
                {'page_number': n_page})

            expected = {'items': [{
                'series_id': self.series_id,
                'volume_id': self.volume_id,
                'user_id': self.user_id,
                'page_number': n_page,
            }]}
            response = self.api.get(
                '/series/{}/reader_progress'.format(self.series_id)).json_body
            for key in ('last_updated',):
                for item in response['items']:
                    item.pop(key)
            self.assertEquals(expected, response)

            expected = self.expected_series_full
            expected['volumes'][0]['progress'] = {
                'series_id': self.series_id,
                'volume_id': self.volume_id,
                'user_id': self.user_id,
                'page_number': n_page,
            }
            response = self.api.get(
                '/series/{}'.format(self.series_id)).json_body
            for key in ('last_updated',):
                for item in response['volumes']:
                    item['progress'].pop(key)
            self.assertEquals(expected, response)

    def test_reprocess_images(self):
        self.api.post_json('/reprocess_images', {
            'width': 860,
            'blur_radius': 16,
        })
        response = self.api.get('/series/{}/cover.jpg'.format(self.series_id))
        self.assertEquals(response.content_type, 'image/jpeg')
        self.api.post_json('/reprocess_images', {
            'width': 860,
            'as_thumbnail': True,
        })
        response = self.api.get('/series/{}/cover.jpg'.format(self.series_id))
        self.assertEquals(response.content_type, 'image/jpeg')


class TestSeveralVolumesWithProgress(SingleVolumeInSeriesTest):
    maxDiff = None

    def setUp(self):
        SingleSeriesTest.setUp(self)
        self.done = []
        self.partially_read = []
        self.not_started = []
        for n_read, volume_list in (
                (2, self.done),
                (1, self.partially_read),
                (0, self.not_started),
                ):
            for n_volume in range(1, 3):
                pages = ['page{:x}.jpg'.format(x) for x in range(3)]
                with tmp_cbt(pages) as f:
                    fn = 'volume-{}.cbt'.format(n_volume)
                    volume_id = self.api.post(
                        '/series/{}/volumes'.format(self.series_id),
                        upload_files=[('input', fn, f.read())],
                        content_type='multipart/form-data',
                    ).json_body['volumes'][0]
                volume_list.append(volume_id)
                if n_read > 0:
                    self.api.put_json(
                        '/volumes/{}/reader_progress'.format(volume_id),
                        {'page_number': n_read})

    @property
    def expected_progress_partial(self):
        return [{
            'page_number': 1,
            'series_id': self.series_id,
            'user_id': self.user_id,
            'volume_id': x,
        } for n, x in enumerate(self.partially_read)]

    @property
    def expected_progress_done(self):
        return [{
            'page_number': 2,
            'series_id': self.series_id,
            'user_id': self.user_id,
            'volume_id': x,
        } for x in self.done]

    @property
    def expected_volumes(self):
        return [{
            'id': x,
            'filename': 'volume-{}.cbt'.format(n + 1),
            'volume_number': n + 1,
            'language': None,
            'pages': 3,
            'progress': self.expected_progress_partial[n]
        } for n, x in enumerate(self.partially_read)
        ] + [{
            'id': x,
            'filename': 'volume-{}.cbt'.format(n + 1),
            'volume_number': n + 1,
            'language': None,
            'pages': 3,
            'progress': None,
        } for n, x in enumerate(self.not_started)
        ] + [{
            'id': x,
            'filename': 'volume-{}.cbt'.format(n + 1),
            'volume_number': n + 1,
            'language': None,
            'pages': 3,
            'progress': self.expected_progress_done[n],
        } for n, x in enumerate(self.done)
        ]

    def test_get_overall_progress(self):
        progress = self.expected_progress_partial[::-1]
        progress += self.expected_progress_done[::-1]
        expected = {'items': progress}
        response = self.api.get('/reader_progress').json_body
        for x in response['items']:
            assert x.pop('last_updated')
        assert expected == response

    def test_get_series(self):
        expected = self.expected_series_full
        response = self.api.get('/series/{}'.format(self.series_id)).json_body
        for x in response['volumes']:
            if x['progress']:
                assert x['progress'].pop('last_updated')
        self.assertEquals(expected, response)

    def test_get_next(self):
        for n_volume, volume_id in enumerate(self.partially_read[:-1]):
            response = self.api.get(
                '/volumes/{}/next'.format(volume_id)).json_body
            self.assertEquals(n_volume + 2, response['volume_number'])
        volume_id = self.partially_read[-1]
        response = self.api.get(
            '/volumes/{}/next'.format(volume_id)).json_body
        self.assertEquals(None, response)


class TestSeveralVolumesAndSeries(SingleVolumeInSeriesTest):
    def setUp(self):
        SingleVolumeInSeriesTest.setUp(self)
        self.other_series = []
        for n_series in range(20):
            response = self.api.post_json(
                '/series', {
                    'name': 'Berserk {}'.format(n_series),
                    'description': 'My Description',
                    'genres': ['action', 'meme'],
                    'dbpedia_uri': None,
                    'author': None,
                    'magazine': None,
                    'number_of_volumes': None,
                }
            ).json_body
            self.assertEquals(len(response['series']), 1)
            self.other_series.append(response['series'][0])

    def test_update_series(self):
        self.api.put_json('/volumes/{}'.format(self.volume_id), {
            'series_id': self.other_series[0],
        })
        response = self.api.get('/volumes/{}'.format(self.volume_id)).json_body
        self.assertEquals(response['language'], None)
        self.assertEquals(response['volume_number'], 7)
        self.assertEquals(response['series_id'], self.other_series[0])
