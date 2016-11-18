from contextlib import contextmanager
from tempfile import NamedTemporaryFile

from PIL import Image


@contextmanager
def gen_image(width, height):
    with NamedTemporaryFile() as f:
        im = Image.new('RGB', (width, height))
        im.save(f, 'png')
        f.flush()
        yield f.name


class TestResizeImage(object):
    def setup(self):
        from ..volume import resized_image
        self.fut = resized_image

    def assert_dimensions(self, f, width, height):
        im = Image.open(f)
        assert (width, height) == im.size

    def test_v(self):
        with gen_image(3300, 3000) as filename:
            with self.fut(filename) as f:
                self.assert_dimensions(f, 330, 300)

    def test_h(self):
        with gen_image(3200, 3300) as filename:
            with self.fut(filename) as f:
                self.assert_dimensions(f, 320, 330)

    def test_square(self):
        with gen_image(540, 540) as filename:
            with self.fut(filename) as f:
                self.assert_dimensions(f, 320, 320)


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
