from datetime import datetime

from couchdb.mapping import DateTimeField
from couchdb.mapping import IntegerField
from couchdb.mapping import TextField
from couchdb.mapping import ViewField

from .utils import GodhandDocument


class Bookmark(GodhandDocument):
    class_ = TextField('@class', default='Bookmark')
    user_id = TextField()
    series_id = TextField()
    volume_id = TextField()
    page_number = IntegerField()
    max_spread = IntegerField()
    number_of_pages = IntegerField()
    last_updated = DateTimeField()
    volume_number = IntegerField()

    @classmethod
    def _key(cls, user_id, volume_id):
        return '{}:{}'.format(user_id, volume_id)

    @classmethod
    def update(cls, db, user_id, volume, page_number):
        key = cls._key(user_id=user_id, volume_id=volume.id)
        instance = cls.load(db, key)
        if not instance:
            instance = cls(
                id=key,
                user_id=user_id,
                series_id=volume.series_id,
                volume_id=volume.id,
                volume_number=volume.volume_number,
                number_of_pages=len(volume.pages),
            )
        instance.page_number = page_number
        instance.last_updated = datetime.utcnow()
        instance.max_spread = volume.get_max_spread(page_number)
        instance.store(db)
        cls.sync(db)
        return instance

    @classmethod
    def sync(cls, db):
        cls.by_user_id_series.sync(db)

    by_user_id_series = ViewField('bookmarks-by-user_id-series', '''
    function(doc) {
        if (doc['@class'] === 'Bookmark') {
            emit([
                doc.user_id,
                doc.series_id,
                doc.last_updated
            ], {_id: doc.id});
        }
    }
    ''')

    @classmethod
    def query(cls, db, user_id, series_id=None, include_docs=True):
        startkey = [user_id]
        if series_id:
            startkey.append(series_id)
        return cls.by_user_id_series(
            db,
            descending=True,
            startkey=startkey + [{}],
            endkey=startkey,
            include_docs=include_docs,
        )

    def as_dict(self):
        return {
            'series_id': self.series_id,
            'volume_id': self.volume_id,
            'max_spread': self.max_spread or 1,
            'number_of_pages': self.number_of_pages,
            'page_number': self.page_number,
            'last_updated': self.last_updated.isoformat(),
            'volume_number': self.volume_number,
        }
