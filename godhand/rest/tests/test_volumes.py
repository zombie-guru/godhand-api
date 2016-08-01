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
            'volumes': [{
                '@class': 'Volume',
                '_id': volume_id,
                'volume_number': 7,
                'filename': 'volume-007.cbt',
            }],
            'offset': 0, 'total': 1, 'limit': 10,
        }
        response = self.api.get('/volumes').json_body
        for volume in response['volumes']:
            assert len(volume.pop('pages')) == 15
            assert volume.pop('_rev')
        self.assertEquals(expected, response)
        # Get the volume by the key
        expected = {
            '@class': 'Volume',
            '_id': volume_id,
            'volume_number': 7,
            'filename': 'volume-007.cbt',
        }
        response = self.api.get('/volumes/{}'.format(volume_id)).json_body
        response.pop('_rev')
        pages = response.pop('pages')
        self.assertEquals(expected, response)
        self.assertEquals(
            ['page{:x}.jpg'.format(x) for x in range(15)],
            [os.path.basename(x['url']) for x in pages]
        )
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
