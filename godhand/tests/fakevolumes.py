from tempfile import NamedTemporaryFile
import contextlib
import os
import tarfile
import zipfile

from PIL import Image


class CbtFile(object):
    ext = '.cbt'

    @property
    def pages(self):
        widths = (256, 128, 64)
        heights = (128, 128, 128)
        orientation = ('horizontal', 'horizontal', 'vertical')
        return [{
            'filename': 'base/path/page-{:x}.png'.format(n),
            'width': widths[n % 3],
            'height': heights[n % 3],
            'orientation': orientation[n % 3],
            'black_pixel': (n, n),
        } for n in range(15)]

    @property
    def expected_pages(self):
        return [
            dict(
                width=x['width'],
                height=x['height'],
                orientation=x['orientation'],
                filename=os.path.join('original', x['filename']),
            )
            for x in self.pages]
        pass

    @contextlib.contextmanager
    def packaged(self):
        with NamedTemporaryFile() as f:
            with tarfile.open(fileobj=f, mode='w') as ar:
                for o in self.pages:
                    with NamedTemporaryFile() as mf:
                        im = Image.new(
                            'RGB', (o['width'], o['height']))
                        im.putpixel(o['black_pixel'], (0xfe, 0xfe, 0xfe))
                        im.save(mf, 'png')
                        mf.flush()
                        ar.add(mf.name, o['filename'])
            f.flush()
            f.seek(0)
            yield f


class CbzFile(CbtFile):
    ext = '.cbz'

    @contextlib.contextmanager
    def packaged(self):
        with NamedTemporaryFile() as f:
            with zipfile.ZipFile(f, mode='w') as ar:
                for o in self.pages:
                    with NamedTemporaryFile() as mf:
                        im = Image.new(
                            'RGB', (o['width'], o['height']))
                        im.putpixel(o['black_pixel'], (0xfe, 0xfe, 0xfe))
                        im.save(mf, 'png')
                        mf.flush()
                        ar.write(mf.name, o['filename'])
                ar.writestr('derp.db', 'abcedfg')
            f.flush()
            f.seek(0)
            yield f
