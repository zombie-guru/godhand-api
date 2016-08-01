from .utils import ApiTest
from .utils import tmp_cbt


class TestEmpty(ApiTest):
    def test_create_series(self):
        # retrieve all series
        expected = {'series': [], 'offset': 0, 'total': 0, 'limit': 10}
        response = self.api.get('/series').json_body
        self.assertEquals(expected, response)
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
        # get all series
        expected = {
            'series': [{
                '@class': 'Series',
                '_id': series_id,
                'name': 'Berserk',
                'description': 'My Description',
                'genres': ['action', 'meme'],
                'author': None,
                'magazine': None,
                'number_of_volumes': None,
                'volumes': [],
            }],
            'offset': 0,
            'total': 1,
            'limit': 10,
        }
        response = self.api.get('/series').json_body
        for series in response['series']:
            assert series.pop('_rev')
        self.assertEquals(expected, response)
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

        # create more series and try pagination
        for _ in range(99):
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
        response = r0 = self.api.get('/series').json_body
        self.assertEquals(len(response['series']), 10)
        self.assertEquals(response['offset'], 0)
        self.assertEquals(response['limit'], 10)
        self.assertEquals(response['total'], 100)
        response = r1 = self.api.get(
            '/series', params={'offset': 5, 'limit': 2}).json_body
        self.assertEquals(len(response['series']), 2)
        self.assertEquals(response['offset'], 5)
        self.assertEquals(response['limit'], 2)
        self.assertEquals(response['total'], 100)

        self.assertNotEquals(r0['series'][:2], r1['series'][:2])
