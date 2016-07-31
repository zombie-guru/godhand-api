class TestBatched(object):
    def setup(self):
        from godhand.utils import batched
        self.fut = batched

    def test_zero(self):
        gen = []
        expected = []
        response = list(self.fut(gen, 5000))
        assert expected == response

    def test_one_batch(self):
        gen = range(500)
        expected = [list(range(500))]
        response = list(self.fut(gen, 5000))
        assert expected == response

    def test_one_full(self):
        gen = range(5000)
        expected = [list(range(5000))]
        response = list(self.fut(gen, 5000))
        assert expected == response

    def test_two_batches(self):
        gen = range(5500)
        expected = [list(range(5000)), list(range(5000, 5500))]
        response = list(self.fut(gen, 5000))
        assert expected == response

    def test_two_batches_full(self):
        gen = range(10000)
        expected = [list(range(5000)), list(range(5000, 10000))]
        response = list(self.fut(gen, 5000))
        assert expected == response
