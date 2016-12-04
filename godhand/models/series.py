from datetime import datetime

from couchdb.mapping import DateTimeField
from couchdb.mapping import Document
from couchdb.mapping import IntegerField
from couchdb.mapping import ListField
from couchdb.mapping import TextField
from couchdb.mapping import ViewField

from .utils import GodhandDocument


class SeriesBase(GodhandDocument):
    name = TextField()
    description = TextField()
    author = TextField()
    magazine = TextField()
    number_of_volumes = IntegerField()
    genres = ListField(TextField())

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

    def add_volume(self, db, owner_id, volume):
        raise NotImplementedError()


class Series(SeriesBase):
    class_ = TextField('@class', default='Series')

    @classmethod
    def create(cls, db, *, id=None, **kws):
        if not id:
            id = cls.generate_id()
        doc = cls(id=id, **kws)
        doc.store(db)
        Series.by_name.sync(db)
        return doc

    by_name = ViewField('series-by-name', '''
    function(doc) {
        if (doc['@class'] === 'Series') {
            emit([0, doc.name.toLowerCase()], {_id: doc.id});
        }
    }
    ''')

    @classmethod
    def query(cls, db, name_q=None, include_docs=True):
        if name_q:
            startkey = [0, name_q.lower()]
            endkey = [0, name_q.lower() + cls.MAX_STRING]
        else:
            startkey = [0]
            endkey = [0, {}]
        return cls.by_name(
            db, startkey=startkey, endkey=endkey, include_docs=include_docs)

    def add_volume(self, db, owner_id, volume):
        collection = VolumeCollection.from_series(db, self, owner_id)
        collection.add_volume(db, owner_id, volume)


class VolumeCollection(SeriesBase):
    class_ = TextField('@class', default='VolumeCollection')
    owner_id = TextField()

    @classmethod
    def from_series(cls, db, series, owner_id):
        key = 'VolumeCollection:{}:{}'.format(series.id, owner_id)
        instance = cls.load(db, key)
        if not instance:
            instance = cls(
                id=key,
                name=series.name,
                description=series.description,
                author=series.author,
                magazine=series.magazine,
                number_of_volumes=series.number_of_volumes,
                genres=series.genres,
                owner_id=owner_id,
            )
            instance.store(db)
        return instance

    by_owner_name = ViewField('volume-collections-by-owner-name', '''
    function(doc) {
        if (doc['@class'] === 'VolumeCollection') {
            emit([doc.owner_id, doc.name], {_id: doc.id});
        }
    }
    ''')

    @classmethod
    def query(cls, db, owner_id, include_docs=True):
        return cls.by_owner_name(
            db,
            startkey=[owner_id],
            endkey=[owner_id, {}],
            include_docs=include_docs,
        )

    def add_volume(self, db, owner_id, volume):
        volume.set_volume_collection(db, self)


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
