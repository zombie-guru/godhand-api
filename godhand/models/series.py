from datetime import datetime

from couchdb.mapping import DateTimeField
from couchdb.mapping import Document
from couchdb.mapping import DictField
from couchdb.mapping import IntegerField
from couchdb.mapping import ListField
from couchdb.mapping import Mapping
from couchdb.mapping import TextField
from couchdb.mapping import ViewField
import couchdb.http

from .volume import Volume


class Series(Document):
    class_ = TextField('@class', default='Series')
    name = TextField()
    description = TextField()
    author = TextField()
    magazine = TextField()
    number_of_volumes = IntegerField()
    genres = ListField(TextField())
    cover_page = DictField(Mapping.build(
        volume_id=TextField(),
        page_number=IntegerField(),
    ))
    uploaded_volumes = IntegerField(default=0)

    by_attribute = ViewField('by_attribute', '''
    function(doc) {
        if (doc['@class'] === 'Series') {
            var name = doc.name.toLowerCase();
            emit([null, 'name:' + name], doc);
            emit([doc.uploaded_volumes > 0, 'name:' + name], doc);
            doc.genres.map(function(genre) {
                genre = genre.toLowerCase();
                emit([null, 'genre:' + genre, name], doc);
                emit([doc.uploaded_volumes > 0, 'genre:' + genre, name], doc);
            })
        }
    }
    ''')

    @classmethod
    def create(cls, db, **kws):
        doc = cls(**kws)
        doc.store(db)
        Series.by_attribute.sync(db)
        return doc

    @classmethod
    def query(cls, db, genre=None, name=None, include_empty=False,
              full_match=False):
        if genre is not None and name is not None:
            raise ValueError('Only genre or name can be supplied')
        kws = {
            'startkey': [None if include_empty else True],
            'endkey': [None if include_empty else True],
            'limit': 50,
        }
        if genre:
            genre = genre.lower()
            kws['startkey'].extend(['genre:' + genre, None])
            if full_match:
                kws['endkey'].extend(['genre:' + genre, {}])
            else:
                kws['endkey'].extend([u'genre:' + genre + u'\ufff0'])
        elif name:
            name = name.lower()
            kws['startkey'].append('name:' + name)
            if full_match:
                kws['endkey'].append('name:' + name)
            else:
                kws['endkey'].append(u'name:' + name + u'\ufff0')
        else:
            kws['startkey'].append('name:')
            kws['endkey'].append(u'name:\ufff0')
        return Series.by_attribute(db, **kws)

    def get_volumes_and_progress(self, db, user_id):
        """
        Mult-sort by the following attributes.

        1. All pages read go last.
        2. Partially read pages go first.
        3. Otherwise, sort by volume_number.
        """
        progress = SeriesReaderProgress.retrieve_for_user(db, user_id, self.id)
        progress = {x.volume_id: dict(x.items()) for x in progress}
        volumes = [
            dict(x.items(), progress=progress.get(x.id, None))
            for x in Volume.summary_by_series(
                db, startkey=[self.id], endkey=[self.id, {}])
        ]
        volumes.sort(key=lambda x: (
            x['progress']['page_number'] == x['pages'] - 1
            if x['progress'] else False,
            x['progress'] is None,
            x['volume_number'],
        ))
        return volumes


class SeriesReaderProgress(Document):
    class_ = TextField('@class', default='SeriesReaderProgress')
    user_id = TextField()
    series_id = TextField()
    volume_id = TextField()
    page_number = IntegerField()
    last_updated = DateTimeField()

    @classmethod
    def save_for_user(cls, db, user_id, series_id, volume_id, page_number):
        id = 'progress:{}:{}'.format(volume_id, user_id)
        doc = cls.load(db, id)
        if doc is None:
            doc = cls(id=id)
        doc.user_id = user_id
        doc.series_id = series_id
        doc.volume_id = volume_id
        doc.page_number = page_number
        doc.last_updated = datetime.utcnow()
        doc.store(db)
        cls.by_series.sync(db)
        cls.by_last_read.sync(db)

    @classmethod
    def retrieve_for_user(cls, db, user_id, series_id=None, limit=50):
        if series_id:
            try:
                return cls.by_series(
                    db,
                    startkey=[user_id, series_id, {}],
                    endkey=[user_id, series_id, None],
                    descending=True,
                    limit=limit,
                ).rows
            except couchdb.http.ResourceNotFound:
                return []
        else:
            try:
                return cls.by_last_read(
                    db,
                    startkey=[user_id, {}],
                    endkey=[user_id, None],
                    descending=True,
                    limit=limit,
                ).rows
            except couchdb.http.ResourceNotFound:
                return []

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
