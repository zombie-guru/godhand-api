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
from couchdb.mapping import ViewField

from .. import bookextractor

image_regex = re.compile('^.*\.(jpg|jpeg|gif|png|tiff)$', re.IGNORECASE)


class Volume(Document):
    @classmethod
    def from_archieve(cls, books_path, filename, fd, series_id):
        basedir = mkdtemp(dir=books_path)
        try:
            ext = bookextractor.from_filename(filename)(fd, basedir)
            pages = ext.iter_pages()
            pages = filter(image_regex.match, pages)
            return cls(
                filename=filename,
                volume_number=guess_volume_number(filename),
                pages=[get_image_meta(page) for page in pages],
                series_id=series_id,
            )
        except Exception:
            rmtree(basedir)
            raise

    @classmethod
    def get_series_volume(cls, db, series_id, index):
        """ Get a volume by series and index offset.

        Return None if does not exist or the volume object.
        """
        view = cls.by_series(
            db,
            startkey=[series_id, None],
            endkey=[series_id, {}],
            skip=index,
            limit=1,
        )
        return view.rows[0]

    class_ = TextField('@class', default='Volume')
    filename = TextField()
    volume_number = IntegerField()
    series_id = TextField()
    pages = ListField(DictField(Mapping.build(
        path=TextField(),
        width=IntegerField(),
        height=IntegerField(),
        orientation=TextField(),
    )))

    by_series = ViewField('volume_by_series', '''
    function(doc) {
        if (doc['@class'] === 'Volume') {
            emit([doc.series_id, doc.volume_number], doc);
        }
    }
    ''')


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
