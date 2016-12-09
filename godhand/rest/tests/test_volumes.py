from .utils import SingleVolumeTest
from .utils import SeveralVolumesTest


class TestSingleVolume(SingleVolumeTest):
    def test_get_volume(self):
        expected = self.expected_volume
        response = self.api.get('/volumes/{}'.format(self.volume_id)).json_body
        self.assertEquals(expected, response)

    def test_get_volume_forbidden(self):
        self.oauth2_login('derp@herp.com')
        self.api.get('/volumes/{}'.format(self.volume_id), status=403)

    def test_get_cover(self):
        response = self.api.get('/volumes/{}/cover.jpg'.format(self.volume_id))
        self.assertEquals('image/jpeg', response.content_type)

    def test_get_cover_forbidden(self):
        self.oauth2_login('derp@herp.com')
        self.api.get(
            '/volumes/{}/cover.jpg'.format(self.volume_id), status=403)

    def test_update_bookmark(self):
        for n_page in range(14):
            self.api.put_json(
                '/volumes/{}/bookmark'.format(self.volume_id),
                {'page_number': n_page},
            )
            bookmarks = [{
                'page_number': n_page,
                'volume_id': self.volume_id,
                'series_id': self.user_series_id,
                'max_spread': 1,
                'number_of_pages': 15,
                'volume_number': 7,
            }]
            expected = dict(
                self.expected_user_series_full, bookmarks=bookmarks)
            response = self.api.get(
                '/series/{}'.format(self.user_series_id)).json_body
            for x in response['bookmarks']:
                self.assertIsNotNone(x.pop('last_updated'))
            self.assertEquals(expected, response)

            expected = {'items': bookmarks}
            response = self.api.get('/bookmarks').json_body
            for x in response['items']:
                self.assertIsNotNone(x.pop('last_updated'))
            self.assertEquals(expected, response)


class TestSeveralVolumes(SeveralVolumesTest):
    def test_get_volume(self):
        for n_volume in range(self.n_volumes - 1):
            expected = dict(
                self.get_expected_volume(n_volume),
                next=self.get_expected_volume_short(n_volume + 1)
            )
            response = self.api.get(
                '/volumes/{}'.format(self.volume_ids[n_volume])).json_body
            self.assertEquals(expected, response)

        n_volume = self.n_volumes - 1
        expected = dict(self.get_expected_volume(n_volume), next=None)
        response = self.api.get(
            '/volumes/{}'.format(self.volume_ids[n_volume])).json_body
        self.assertEquals(expected, response)

    def test_get_cover(self):
        for volume_id in self.volume_ids:
            response = self.api.get('/volumes/{}/cover.jpg'.format(volume_id))
            self.assertEquals('image/jpeg', response.content_type)

    def test_get_cover_forbidden(self):
        self.oauth2_login('derp@herp.com')
        for volume_id in self.volume_ids:
            self.api.get('/volumes/{}/cover.jpg'.format(volume_id), status=403)

    def test_get_volume_file(self):
        volume = self.get_expected_volume(0)
        self.assertTrue(len(volume['pages']) > 0)
        for page in volume['pages']:
            filename = page['filename']
            self.api.get('/volumes/{}/files/{}'.format(
                volume['id'], filename))

    def test_get_volume_file_forbidden(self):
        self.oauth2_login('derp@herp.com')
        volume = self.get_expected_volume(0)
        self.assertTrue(len(volume['pages']) > 0)
        for page in volume['pages']:
            filename = page['filename']
            self.api.get('/volumes/{}/files/{}'.format(
                volume['id'], filename), status=403)

    def test_update_bookmark(self):
        volume_id = self.volume_ids[0]
        for n_page in range(14):
            self.api.put_json(
                '/volumes/{}/bookmark'.format(volume_id),
                {'page_number': n_page})
            bookmarks = [{
                'page_number': n_page,
                'volume_id': volume_id,
                'series_id': self.user_series_id,
                'max_spread': 1,
                'number_of_pages': 15,
                'volume_number': 0,
            }]
            expected = dict(
                self.expected_user_series_full,
                bookmarks=bookmarks,
            )
            response = self.api.get(
                '/series/{}'.format(self.user_series_id)).json_body
            for x in response['bookmarks']:
                self.assertIsNotNone(x.pop('last_updated'))
            self.assertEquals(expected, response)

            expected = {'items': bookmarks}
            response = self.api.get('/bookmarks').json_body
            for x in response['items']:
                self.assertIsNotNone(x.pop('last_updated'))
            self.assertEquals(expected, response)

    def test_bookmark_ordering(self):
        """ Bookmarks should be ordered backwards in time.
        """
        bookmarks = [{
            'page_number': 4,
            'volume_id': self.volume_ids[n_volume],
            'series_id': self.user_series_id,
            'max_spread': 1,
            'number_of_pages': 15,
            'volume_number': n_volume,
        } for n_volume in range(self.n_volumes - 1, -1, -1)]

        for n_volume in range(self.n_volumes):
            volume_id = self.volume_ids[n_volume]
            self.api.put_json(
                '/volumes/{}/bookmark'.format(volume_id),
                {'page_number': 4})
        expected = dict(self.expected_user_series_full, bookmarks=bookmarks)
        response = self.api.get(
            '/series/{}'.format(self.user_series_id)).json_body
        for x in response['bookmarks']:
            self.assertIsNotNone(x.pop('last_updated'))
        self.assertEquals(expected, response)

        expected = {'items': bookmarks}
        response = self.api.get('/bookmarks').json_body
        for x in response['items']:
            self.assertIsNotNone(x.pop('last_updated'))
        self.assertEquals(expected, response)
