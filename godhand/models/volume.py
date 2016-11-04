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


class Volume(Document):
    @classmethod
    def from_archieve(cls, db, filename, fd, series_id):
        from PIL import Image
        from PIL import ImageFilter
        ext = bookextractor.from_filename(filename)(fd)
        doc = cls(
            id=uuid4().hex,
            filename=filename,
            volume_number=guess_volume_number(filename),
            pages=[],
            series_id=series_id,
        )
        doc.store(db)

        doc = db[doc.id]
        try:
            all_pages = []

            pages = []
            with ext.iter_pages() as page_iter:
                for relpath, path in page_iter:
                    all_pages.append(path)
                    path_key = os.path.join('original', relpath)
                    try:
                        with Image.open(path) as im:
                            width, height = im.size
                    except OSError:
                        continue
                    pages.append({
                        'filename': path_key,
                        'width': width,
                        'height': height,
                        'orientation':
                            'vertical' if width < height else 'horizontal',
                    })
                    with open(path, 'rb') as f:
                        db.put_attachment(doc, f, filename=path_key)

                pages.sort(key=lambda x: x['filename'])

                with Image.open(sorted(all_pages)[0]) as im:
                    im.resize(
                        (
                            1980,
                            int(height * 1980 / width)
                        ),
                    )
                    im = im.filter(ImageFilter.GaussianBlur(radius=20))
                    with SpooledTemporaryFile() as f:
                        im.save(f, 'JPEG')
                        f.flush()
                        f.seek(0)
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

    @classmethod
    def collection_for_series(cls, db, series_id, language=None):
        key = []
        if language:
            key.append('language:{}'.format(language))
        key.append('series:{}'.format(series_id))
        return cls.summary_by_series(db, startkey=key, endkey=key + [{}])

    @classmethod
    def reprocess_all_images(cls, db, width, blur_radius, as_thumbnail):
        for volume in cls.by_series(db):
            volume.reprocess_images(db, width, blur_radius, as_thumbnail)

    def get_next_volume(self, db):
        view = self.by_series(
            db,
            start_key=[self.series_id, self.volume_number + 1],
            end_key=[self.series_id, {}],
            limit=1,
        )
        try:
            return view.rows[0]
        except IndexError:
            return None

    def reprocess_images(self, db, width, blur_radius=0, as_thumbnail=False):
        from PIL import Image
        from PIL import ImageFilter
        cover = db.get_attachment(self, self.pages[0]['filename'])
        if cover is None:
            LOG.warn('Could not get cover for Volume<{}>.'.format(self.id))
            return
        try:
            with Image.open(cover) as im:
                _width, _height = im.size
                if as_thumbnail:
                    im.thumbnail((width, int(_height * width / _width)))
                else:
                    im = im.resize((width, int(_height * width / _width)))
                if blur_radius:
                    im = im.filter(ImageFilter.GaussianBlur(blur_radius))
                with SpooledTemporaryFile() as f:
                    im.save(f, 'JPEG')
                    f.flush()
                    f.seek(0)
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
        self.summary_by_series.sync(db)
        Series.by_attribute.sync(db)
        return self

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
            var sKey = 'series:' + doc.series_id;
            var lKey = 'language:' + doc.language;
            var nKey = 'language:' + doc.volume_number;
            var value = {
                _id: doc._id,
                filename: doc.filename,
                volume_number: doc.volume_number,
                language: doc.language,
                '@class': doc['@class'],
                pages: doc.pages.length
            };
            emit([sKey, nKey], doc);
            emit([lKey, sKey, nKey], doc);
        }
    }
    ''')

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
