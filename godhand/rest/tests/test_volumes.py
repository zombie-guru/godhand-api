import os

from .utils import ApiTest
from .utils import tmp_cbt


class TestEmpty(ApiTest):
    def test_create_volume(self):
        # retrieve volumes
        expected = {'volumes': [], 'offset': 0, 'total': 0, 'limit': 10}
        response = self.api.get('/volumes').json_body
        self.assertEquals(expected, response)
        # create a volume
        with tmp_cbt(['page{:x}.jpg'.format(x) for x in range(15)]) as f:
            response = self.api.post(
                '/volumes',
                upload_files=[('input', 'volume-007.cbt', f.read())],
                content_type='multipart/form-data',
            ).json_body
        self.assertEquals(len(response['volumes']), 1)
        volume_id = response['volumes'][0]
        # get all volumes
        expected = {
            'volumes': [{'id': volume_id, 'volume_number': 7}],
            'offset': 0, 'total': 1, 'limit': 10,
        }
        response = self.api.get('/volumes').json_body
        self.assertEquals(expected, response)
        # Get the volume by the key
        expected = {'id': volume_id, 'volume_number': 7}
        response = self.api.get('/volumes/{}'.format(volume_id)).json_body
        pages = response.pop('pages')
        self.assertEquals(expected, response)
        self.assertEquals(
            ['page{:x}.jpg'.format(x) for x in range(15)],
            [os.path.basename(x['url']) for x in pages]
        )
        for n_page, page in enumerate(pages):
            response = self.api.get(page['url'])
            self.assertEquals(
                'content of page{:x}.jpg'.format(n_page).encode('utf-8'),
                response.body)
        # update meta data
        self.api.put_json('/volumes/{}'.format(volume_id), {
            'volume_number': 17
        })
        response = self.api.get('/volumes/{}'.format(volume_id)).json_body
        self.assertEquals(response['volume_number'], 17)
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
        # add to series
        self.api.put_json(
            '/series/{}/volumes/{}'.format(series_id, volume_id)
        )
        expected = {
            'id': series_id,
            'name': 'Berserk',
            'description': 'My Description',
            'genres': ['action', 'meme'],
            'volumes': [{
                'id': volume_id,
                'volume_number': 17,
            }],
            'dbpedia_uri': None,
            'author': None,
            'magazine': None,
            'number_of_volumes': None,
        }
        response = self.api.get('/series/{}'.format(series_id)).json_body
        self.assertEquals(expected, response)
        expected = {'series': [{
            'id': series_id,
            'name': 'Berserk',
            'description': 'My Description',
            'genres': ['action', 'meme'],
            'dbpedia_uri': None,
            'author': None,
            'magazine': None,
            'number_of_volumes': None,
        }], 'limit': 10, 'offset': 0, 'total': 1}
        response = self.api.get('/series').json_body
        self.assertEquals(expected, response)
