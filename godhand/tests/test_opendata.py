class TestLoadMangaResource(object):
    def setup(self):
        from godhand.opendata import load_manga_resource
        self.fut = load_manga_resource

    def test_load_berserk(self):
        keys = [
            'description', 'name', 'author', 'number_of_volumes', 'magazine',
            'genre',
        ]
        uri = 'http://dbpedia.org/resource/Berserk_(manga)'
        response = self.fut(uri)
        for key in keys:
            assert len(response[key]) > 0
        assert all(isinstance(x, int) for x in response['number_of_volumes'])
