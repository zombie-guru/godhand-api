class TestVolume(object):
    def setup(self):
        from ..volume import Volume
        self.cls = Volume

    def test_get_max_spread_vv(self):
        instance = self.cls(pages=[
            {'orientation': 'vertical'},
            {'orientation': 'vertical'},
        ])
        expected = 2
        response = instance.get_max_spread(0)
        assert expected == response

    def test_get_max_spread_vh(self):
        instance = self.cls(pages=[
            {'orientation': 'vertical'},
            {'orientation': 'horizontal'},
        ])
        expected = 1
        response = instance.get_max_spread(0)
        assert expected == response

    def test_get_max_spread_hv(self):
        instance = self.cls(pages=[
            {'orientation': 'horizontal'},
            {'orientation': 'vertical'},
        ])
        expected = 1
        response = instance.get_max_spread(0)
        assert expected == response

    def test_get_max_spread_v(self):
        instance = self.cls(pages=[
            {'orientation': 'vertical'},
        ])
        expected = 1
        response = instance.get_max_spread(0)
        assert expected == response

    def test_get_max_spread_h(self):
        instance = self.cls(pages=[
            {'orientation': 'horizontal'},
        ])
        expected = 1
        response = instance.get_max_spread(0)
        assert expected == response
