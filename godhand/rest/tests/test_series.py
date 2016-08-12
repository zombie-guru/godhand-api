from .utils import ApiTest
from .utils import tmp_cbt


class TestEmpty(ApiTest):
    def test_create_series(self):
        # test 404
        self.api.get('/series/missing', status=404)
        # create a series
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

        # test 404 upload
        with tmp_cbt(['page{:x}.jpg'.format(x) for x in range(15)]) as f:
            self.api.post(
                '/series/missing/volumes',
                upload_files=[('input', 'volume-007.cbt', f.read())],
                content_type='multipart/form-data',
                status=404
            )

        # add volume to series
        with tmp_cbt(['page{:x}.jpg'.format(x) for x in range(15)]) as f:
            response = self.api.post(
                '/series/{}/volumes'.format(series_id),
                upload_files=[('input', 'volume-007.cbt', f.read())],
                content_type='multipart/form-data',
            ).json_body
        self.assertEquals(len(response['volumes']), 1)
        volume_id = response['volumes'][0]

        expected = {
            '@class': 'Series',
            '_id': series_id,
            'name': 'Berserk',
            'description': 'My Description',
            'genres': ['action', 'meme'],
            'volumes': [
                {
                    'id': volume_id,
                    'volume_number': 7,
                }
            ],
            'author': None,
            'magazine': None,
            'number_of_volumes': None,
        }
        response = self.api.get('/series/{}'.format(series_id)).json_body
        assert response.pop('_rev')
        self.assertEquals(expected, response)

        # store and get series progress
        expected = {'volume_number': 0, 'page_number': 0}
        response = self.api.get(
            '/series/{}/reader-progress'.format(series_id)).json_body
        for key in ('_id', '_rev', '@class'):
            response.pop(key, None)
        self.assertEquals(expected, response)

        self.api.put_json(
            '/series/{}/reader-progress'.format(series_id),
            {'volume_number': 432, 'page_number': 7})
        expected = {'volume_number': 432, 'page_number': 7}
        response = self.api.get(
            '/series/{}/reader-progress'.format(series_id)).json_body
        for key in ('_id', '_rev', '@class'):
            response.pop(key, None)
        self.assertEquals(expected, response)

        self.api.put_json(
            '/series/missing/reader-progress',
            {'volume_number': 432, 'page_number': 7}, status=404)
        self.api.get('/series/missing/reader-progress', status=404)
