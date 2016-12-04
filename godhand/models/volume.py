from contextlib import contextmanager
from tempfile import SpooledTemporaryFile
from uuid import uuid4
import logging
import os
import re

from couchdb.mapping import DictField
from couchdb.mapping import Document
from couchdb.mapping import IntegerField
from couchdb.mapping import ListField
from couchdb.mapping import Mapping
from couchdb.mapping import TextField
from couchdb.mapping import ViewField

from .. import bookextractor

LOG = logging.getLogger('godhand')


@contextmanager
def resized_image(filename, min_width=320, min_height=300):
    from PIL import Image
    with Image.open(filename) as im:
        width, height = im.size
        if height >= width:
            new_height = int(height * min_width / width)
            new_width = min_width
        else:
            new_height = min_height
            new_width = int(width * min_height / height)
        im = im.resize((new_width, new_height))
        with SpooledTemporaryFile() as f:
            im.save(f, 'JPEG')
            f.flush()
            f.seek(0)
            yield f


class Volume(Document):
    @classmethod
    def from_archieve(cls, db, owner_id, filename, fd):
        from PIL import Image
        ext = bookextractor.from_filename(filename)(fd)
        doc = cls(
            id=uuid4().hex,
            filename=filename,
            volume_number=guess_volume_number(filename),
            pages=[],
            owner_id=owner_id,
        )
        doc.store(db)

        doc = db[doc.id]
        try:
            all_pages = []

            pages = []
            with ext.iter_pages() as page_iter:
                for relpath, path in page_iter:
                    path_key = os.path.join('original', relpath)
                    try:
                        with Image.open(path) as im:
                            width, height = im.size
                    except OSError:
                        continue
                    all_pages.append(path)
                    pages.append({
                        'filename': path_key,
                        'filesize': os.stat(path).st_size,
                        'width': width,
                        'height': height,
                        'orientation':
                            'vertical' if width < height else 'horizontal',
                    })
                    with open(path, 'rb') as f:
                        db.put_attachment(doc, f, filename=path_key)

                pages.sort(key=lambda x: x['filename'])

                with resized_image(sorted(all_pages)[0]) as f:
                    db.put_attachment(doc, f, filename='cover.jpg')

            doc = db[doc.id]
            doc['pages'] = pages
            db.save(doc)
            return cls.load(db, doc.id)
        except Exception:
            doc = cls.load(db, doc.id)
            db.delete(doc)
            raise
        finally:
            cls.by_series.sync(db)
            cls.user_usage.sync(db)

    @classmethod
    def get_series_volume(cls, db, series_id, index, owner_id):
        """ Get a volume by series and index offset.

        Return None if does not exist or the volume object.
        """
        return cls.query(
            db,
            owner_id=owner_id,
            series_id=series_id,
            skip=index,
            total=1,
        ).rows[0]

    @classmethod
    def reprocess_all_images(cls, db, min_width, min_height):
        for volume in cls.iterall(db):
            volume.reprocess_images(db, min_width, min_height)

    def set_volume_collection(self, db, collection):
        self.series_id = collection.id
        self.store(db)

    def get_next_volume(self, db, owner_id):
        rows = self.query(
            db,
            series_id=self.series_id,
            min_volume_number=self.volume_number + 1,
            owner_id=owner_id,
            total=1,
        ).rows
        try:
            return rows[0]
        except IndexError:
            return None

    def reprocess_images(self, db, min_width, min_height):
        cover = db.get_attachment(self, self.pages[0]['filename'])
        if cover is None:
            LOG.warn('Could not get cover for Volume<{}>.'.format(self.id))
            return
        try:
            with resized_image(cover, min_width, min_height) as f:
                db.put_attachment(self, f, filename='cover.jpg')
        finally:
            cover.close

    def update_meta(self, db, language=None, volume_number=None, series=None):
        from .series import Series
        if language:
            self.language = language
        if volume_number:
            self.volume_number = volume_number
        current_series = Series.load(db, self.series_id)
        if series:
            current_series = Series.load(db, self.series_id)
            if current_series and current_series.id != series.id:
                current_series.move_volume_to(db, series, self)
                self.series_id = series.id
        else:
            current_series.update_volume_meta(db, self)
        self.store(db)
        self.by_series.sync(db)
        Series.by_attribute.sync(db)
        return self

    def delete_file(self, db, filename):
        from .series import Series
        self.pages = filter(lambda x: x.filename != filename, self.pages)
        self.store(db)
        series = Series.load(db, self.series_id)
        series.update_volume_meta(db, self)
        Series.by_attribute.sync(db)

        db.delete_attachment(self, filename)
        self.by_series.sync(db)

    def delete(self, db):
        from .series import Series
        series = Series.load(db, self.series_id)
        series.delete_volume(db, self)
        db.delete(self)
        self.by_series.sync(db)

    class_ = TextField('@class', default='Volume')
    filename = TextField()
    volume_number = IntegerField()
    language = TextField()
    series_id = TextField()
    owner_id = TextField()
    pages = ListField(DictField(Mapping.build(
        filename=TextField(),
        width=IntegerField(),
        height=IntegerField(),
        filesize=IntegerField(),
        orientation=TextField(),
    )))

    by_series = ViewField('volume_by_series', '''
    function(doc) {
        if (doc['@class'] === 'Volume') {
            emit([
                0,
                doc.owner_id,
                doc.language,
                doc.series_id,
                doc.volume_number,
            ],
            doc);

            emit([
                1,
                doc.owner_id,
                doc.series_id,
                doc.volume_number,
            ],
            doc);
        }
    }
    ''')

    @classmethod
    def query(
            cls, db, owner_id, *,
            min_volume_number=None,
            language=None, series_id=None, skip=0, total=100):
        if isinstance(min_volume_number, int) and not series_id:
            raise ValueError('series_id required with min_volume_number')

        if language:
            startkey = [0, owner_id, language]
        else:
            startkey = [1, owner_id]
        if series_id:
            startkey += [series_id]
        if min_volume_number is not None:
            startkey += [min_volume_number]
        return cls.by_series(
            db,
            startkey=startkey,
            endkey=startkey + [{}],
            skip=skip,
            total=total,
        )

    @classmethod
    def iterall(cls, db):
        return cls.by_series(db, startkey=[1], endkey=[1, {}])

    user_usage = ViewField('user_usage', '''
    function(doc) {
        if (doc['@class'] == 'Volume') {
            var filesize = 0;
            doc.pages.forEach(function(x) {
                filesize = filesize + x.filesize;
            })
            if (filesize > 0) {
                emit([doc.owner_id], filesize);
            }
        }
    }
    ''', '_sum', wrapper=lambda x: x)

    @classmethod
    def get_user_usage(cls, db, user_id):
        rows = cls.user_usage(db, key=[user_id])
        return sum(map(lambda x: x['value'], rows))

    def get_max_spread(self, page_number):
        left_page = self.pages[page_number]
        try:
            right_page = self.pages[page_number + 1]
        except IndexError:
            return 1
        pages = (left_page, right_page)
        if all(x['orientation'] == 'vertical' for x in pages):
            return 2
        return 1

    def as_dict(self, short=False):
        d = {
            'id': self.id,
            'filename': self.filename,
            'volume_number': self.volume_number,
            'language': self.language,
        }
        if short:
            d['pages'] = len(self.pages)
        else:
            d['pages'] = [{
                'filename': x.filename,
                'width': x.width,
                'height': x.height,
                'orientation': x.orientation,
            } for x in self.pages]
            d['series_id'] = self.series_id
        return d


def guess_volume_number(filename):
    try:
        return int(re.findall('\d+', filename)[-1])
    except IndexError:
        return None
