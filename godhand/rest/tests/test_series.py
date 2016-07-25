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
