from datetime import datetime

from couchdb.mapping import DateTimeField
from couchdb.mapping import Document
from couchdb.mapping import IntegerField
from couchdb.mapping import ListField
from couchdb.mapping import TextField
from couchdb.mapping import ViewField

from .utils import GodhandDocument


class Series(GodhandDocument):
    """ Represents a collection of Volume objects.

    # Owner
    if ``owner_id`` is set, that means it belongs to a user. This has the
    property that.

    1. It should be uploadable but only by the owner.
    2. Owner can edit meta data fo this series.

    """
    class_ = TextField('@class', default='Series')
    name = TextField()
    description = TextField()
    author = TextField()
    magazine = TextField()
    number_of_volumes = IntegerField()
    genres = ListField(TextField())
    owner_id = TextField(default='root')

    def as_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'genres': self.genres,
            'author': self.author,
            'magazine': self.magazine,
            'number_of_volumes': self.number_of_volumes,
        }

    @classmethod
    def sync(cls, db):
        cls.by_owner_name.sync(db)

    @classmethod
    def create(cls, db, *, id=None, **kws):
        if not id:
            id = cls.generate_id()
        doc = cls(id=id, **kws)
        doc.store(db)
        cls.sync(db)
        return doc

    by_owner_name = ViewField('series-by-name', '''
    function(doc) {
        if (doc['@class'] === 'Series') {
            emit([doc.owner_id, doc.name.toLowerCase()], {_id: doc.id});
        }
    }
    ''')

    @classmethod
    def query(cls, db, owner_id='root', name_q=None, include_docs=True):
        if name_q:
            startkey = [owner_id, name_q.lower()]
            endkey = [owner_id, name_q.lower() + cls.MAX_STRING]
        else:
            startkey = [owner_id]
            endkey = [owner_id, {}]
        return cls.by_owner_name(
            db, startkey=startkey, endkey=endkey, include_docs=include_docs)

    def _key(self, owner_id):
        return '{}:{}'.format(self.id, owner_id)

    def retrieve_owner_instance(self, db, owner_id):
        if self.owner_id != owner_id:
            key = self._key(owner_id)
            db.copy(self.id, key)
            instance = Series.load(db, key)
            instance.owner_id = owner_id
            instance.store(db)
            return instance
        return self

    def add_volume(self, db, owner_id, volume):
        instance = self.retrieve_owner_instance(db, owner_id)
        volume.set_volume_collection(db, instance)


class SeriesReaderProgress(Document):
    class_ = TextField('@class', default='SeriesReaderProgress')
    user_id = TextField()
    series_id = TextField()
    volume_id = TextField()
    page_number = IntegerField()
    max_spread = IntegerField()
    number_of_pages = IntegerField()
    last_updated = DateTimeField()
    series_name = TextField()
    volume_number = IntegerField()

    @classmethod
    def save_for_user(cls, db, user_id, series_id, volume, page_number):
        id = 'progress:{}:{}'.format(volume.id, user_id)
        doc = cls.load(db, id)
        if doc is None:
            doc = cls(id=id)
        series = Series.load(db, series_id)
        doc.user_id = user_id
        doc.series_id = series_id
        doc.volume_id = volume.id
        doc.page_number = page_number
        doc.last_updated = datetime.utcnow()
        doc.max_spread = volume.get_max_spread(page_number)
        doc.volume_number = volume.volume_number
        doc.number_of_pages = len(volume.pages)
        doc.series_name = series.name
        doc.store(db)
        cls.by_series.sync(db)
        cls.by_last_read.sync(db)

    @classmethod
    def retrieve_for_user(cls, db, user_id, series_id=None, limit=50):
        if series_id:
            return cls.by_series(
                db,
                startkey=[user_id, series_id, {}],
                endkey=[user_id, series_id, None],
                descending=True,
                limit=limit,
            ).rows
        else:
            return cls.by_last_read(
                db,
                startkey=[user_id, {}],
                endkey=[user_id, None],
                descending=True,
                limit=limit,
            ).rows

    by_series = ViewField('progress_by_series', '''
    function(doc) {
        if (doc['@class'] === 'SeriesReaderProgress') {
            emit(
                [
                    doc.user_id,
                    doc.series_id,
                    doc.last_updated
                ],
                doc
            );
        }
    }
    ''')

    by_last_read = ViewField('by_last_read', '''
    function(doc) {
        if (doc['@class'] === 'SeriesReaderProgress') {
            emit(
                [
                    doc.user_id,
                    doc.last_updated,
                ],
                doc
            );
        }
    }
    ''')

    def as_dict(self):
        return {
            'user_id': self.user_id,
            'series_id': self.series_id,
            'volume_id': self.volume_id,
            'max_spread': self.max_spread or 1,
            'number_of_pages': self.number_of_pages or 1000,
            'page_number': self.page_number,
            'last_updated': self.last_updated.isoformat(),
            'series_name': self.series_name,
            'volume_number': self.volume_number,
        }
