from .utils import ApiTest
from .utils import tmp_cbt


class TestEmpty(ApiTest):
    def test_get_books(self):
        expected = {'books': [], 'limit': 10, 'offset': 0, 'total': 0}
        response = self.api.get('/books').json_body
        self.assertEquals(expected, response)

    def test_create_book(self):
        expected = expected_book = {
            'id': 1,
            'title': 'Untitled',
            'pages': list(range(1, 16))
        }
        with tmp_cbt(['page{:x}.jpg'.format(x) for x in range(15)]) as f:
            response = self.api.post(
                '/books',
                upload_files=[('input', 'book.cbt', f.read())],
                content_type='multipart/form-data',
            ).json_body
        self.assertEquals(expected, response)

        expected = {
            'books': [expected_book], 'offset': 0, 'limit': 10, 'total': 1,
        }
        response = self.api.get('/books').json_body
        self.assertEquals(expected, response)

        expected = expected_book
        response = self.api.get('/books/1').json_body
        self.assertEquals(expected, response)

        expected = {
            'pages': [{
                'id': x,
                'mimetype': 'images/jpeg',
            } for x in range(1, 11)],
            'offset': 0,
            'limit': 10,
            'total': 15
        }
        response = self.api.get('/books/1/pages').json_body
        self.assertEquals(expected, response)

        expected = {
            'pages': [{
                'id': x,
                'mimetype': 'images/jpeg',
            } for x in range(11, 16)],
            'offset': 10,
            'limit': 10,
            'total': 15
        }
        response = self.api.get(
            '/books/1/pages', params={'offset': 10}).json_body
        self.assertEquals(expected, response)

        for n_page in range(15):
            response = self.api.get(
                '/books/1/pages/{}'.format(n_page),
                headers={'accept': 'images/*'},
            )
            assert response.content_type == 'images/jpeg'
            expected = 'content of page{:x}.jpg'.format(n_page)
            assert expected == response.body.decode('utf-8')

        self.api.get(
            '/books/1/pages/15', headers={'accept': 'images/*'}, status=404)
