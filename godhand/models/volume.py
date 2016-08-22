from shutil import rmtree
from tempfile import mkdtemp
import re

from PIL import Image
from couchdb.mapping import DictField
from couchdb.mapping import Document
from couchdb.mapping import IntegerField
from couchdb.mapping import ListField
from couchdb.mapping import Mapping
from couchdb.mapping import TextField

from .. import bookextractor

image_regex = re.compile('^.*\.(jpg|jpeg|gif|png|tiff)$', re.IGNORECASE)


class Volume(Document):
    @classmethod
    def from_archieve(cls, books_path, filename, fd):
        basedir = mkdtemp(dir=books_path)
        try:
            ext = bookextractor.from_filename(filename)(fd, basedir)
            pages = ext.iter_pages()
            pages = filter(image_regex.match, pages)
            return cls(
                filename=filename,
                volume_number=guess_volume_number(filename),
                pages=[get_image_meta(page) for page in pages],
            )
        except Exception:
            rmtree(basedir)
            raise

    class_ = TextField('@class', default='Volume')
    filename = TextField()
    volume_number = IntegerField()
    language = TextField()
    pages = ListField(DictField(Mapping.build(
        path=TextField(),
        width=IntegerField(),
        height=IntegerField(),
        orientation=TextField(),
    )))


def guess_volume_number(filename):
    try:
        return int(re.findall('\d+', filename)[-1])
    except IndexError:
        return None


def get_image_meta(filename):
    with Image.open(filename) as im:
        width, height = im.size
        return {
            'path': filename,
            'width': width,
            'height': height,
            'orientation': 'vertical' if width < height else 'horizontal',
        }
