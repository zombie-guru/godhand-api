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


class Volume(Document):
    @classmethod
    def from_archieve(cls, db, filename, fd, series_id):
        ext = bookextractor.from_filename(filename)(fd)
        doc = cls(
            filename=filename,
            volume_number=guess_volume_number(filename),
            pages=[],
            series_id=series_id,
        )
        doc.store(db)

        _doc = db[doc.id]
        try:
            pages = []
            for relpath, path in ext.iter_pages():
                try:
                    pages.append(get_image_meta(path, relpath))
                except OSError:
                    continue
                with open(path, 'rb') as f:
                    db.put_attachment(_doc, f, filename=relpath)
                attachment = db.get_attachment(doc.id, relpath)
                assert attachment

            pages.sort(key=lambda x: x['filename'])

            _doc = db[doc.id]
            _doc['pages'] = pages
            db.save(_doc)
            return doc
        except Exception:
            doc = cls.load(db, doc.id)
            db.delete(doc)
            raise
        cls.by_series.sync(db)
        cls.summary_by_series.sync(db)

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

    def get_next_volume(self, db):
        view = self.by_series(
            db,
            start_key=[self.series_id, self.volume_number + 1],
            limit=1,
        )
        try:
            return view.rows[0]
        except IndexError:
            return None

    class_ = TextField('@class', default='Volume')
    filename = TextField()
    volume_number = IntegerField()
    language = TextField()
    series_id = TextField()
    pages = ListField(DictField(Mapping.build(
        filename=TextField(),
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

    summary_by_series = ViewField('summary_by_series', '''
    function(doc) {
        if (doc['@class'] == 'Volume') {
            emit([doc.series_id, doc.volume_number], {
                _id: doc._id,
                filename: doc.filename,
                volume_number: doc.volume_number,
                language: doc.language,
                '@class': doc['@class'],
                pages: doc.pages.length
            });
        }
    }
    ''')


def guess_volume_number(filename):
    try:
        return int(re.findall('\d+', filename)[-1])
    except IndexError:
        return None


def get_image_meta(filename, relpath):
    with Image.open(filename) as im:
        width, height = im.size
        return {
            'filename': relpath,
            'width': width,
            'height': height,
            'orientation': 'vertical' if width < height else 'horizontal',
        }
