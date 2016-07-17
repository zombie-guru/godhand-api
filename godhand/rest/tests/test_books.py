import os

from .utils import ApiTest
from .utils import tmp_cbt


class TestEmpty(ApiTest):
    def test_create_book(self):
        # retrieve books
        expected = {'books': [], 'offset': 0, 'total': 0}
        response = self.api.get('/books').json_body
        self.assertEquals(expected, response)
        # create a book
        with tmp_cbt(['page{:x}.jpg'.format(x) for x in range(15)]) as f:
            response = self.api.post(
                '/books',
                upload_files=[('input', 'book.cbt', f.read())],
                content_type='multipart/form-data',
            ).json_body
        self.assertEquals(len(response['books']), 1)
        book_id = response['books'][0]
        # get all books
        expected = {
            'books': [{'id': book_id, 'title': 'Untitled'}],
            'offset': 0,
            'total': 1,
        }
        response = self.api.get('/books').json_body
        self.assertEquals(expected, response)
        # Get the book by the key
        expected = {
            'id': book_id,
            'title': 'Untitled',
        }
        response = self.api.get('/books/{}'.format(book_id)).json_body
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
