from .utils import ApiTest


class TestEmpty(ApiTest):
    def test_create_series(self):
        # retrieve all series
        expected = {'series': [], 'offset': 0, 'total': 0}
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
                'id': series_id,
                'name': 'Berserk',
                'description': 'My Description',
                'genres': ['action', 'meme'],
                'dbpedia_uri': None,
                'author': None,
                'magazine': None,
                'number_of_volumes': None,
            }],
            'offset': 0,
            'total': 1,
        }
        response = self.api.get('/series').json_body
        self.assertEquals(expected, response)
        # Get the series by the key
        expected = {
            'id': series_id,
            'name': 'Berserk',
            'description': 'My Description',
            'genres': ['action', 'meme'],
            'volumes': [],
            'dbpedia_uri': None,
            'author': None,
            'magazine': None,
            'number_of_volumes': None,
        }
        response = self.api.get('/series/{}'.format(series_id)).json_body
        self.assertEquals(expected, response)

    def test_create_series_from_dbpedia_uri(self):
        # retrieve all series
        expected = {'series': [], 'offset': 0, 'total': 0}
        response = self.api.get('/series').json_body
        self.assertEquals(expected, response)
        # create a series
        uri = 'http://dbpedia.org/resource/Berserk_(manga)'
        response = self.api.post_json('/series', {'uri': uri}).json_body
        self.assertEquals(len(response['series']), 1)
        series_id = response['series'][0]
        # Get the series by the key
        response = self.api.get('/series/{}'.format(series_id)).json_body
        self.assertEquals(response['dbpedia_uri'], uri)
        self.assertRegex(response['id'], '.{4,}')
        self.assertRegex(response['name'], '.{4,}')
        self.assertRegex(response['description'], '.{4,}')
        self.assertRegex(response['author'], '.{4,}')
        self.assertRegex(response['magazine'], '.{4,}')
        self.assertGreaterEqual(response['number_of_volumes'], 37)
        self.assertGreater(len(response['genres']), 1)
        self.assertEquals(response['volumes'], [])

    def test_non_manga_uri(self):
        uri = 'http://dbpedia.org/resource/Ken_Griffey_Jr.'
        self.api.post_json('/series', {'uri': uri}, status=400)
