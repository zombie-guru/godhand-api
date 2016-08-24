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
    volumes = ListField(DictField(Mapping.build(
        id=TextField(),
        volume_number=IntegerField(),
    )))

    by_attribute = ViewField('by_attribute', '''
    function(doc) {
        if (doc['@class'] === 'Series') {
            var name = doc.name.toLowerCase();
            emit([null, 'name:' + name], doc);
            emit([doc.volumes.length > 0, 'name:' + name], doc);
            doc.genres.map(function(genre) {
                genre = genre.toLowerCase();
                emit([null, 'genre:' + genre, name], doc);
                emit([doc.volumes.length > 0, 'genre:' + genre, name], doc);
            })
        }
    }
    ''')

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

    def add_volume(self, volume):
        self.volumes.append(
            {'id': volume.id, 'volume_number': volume.volume_number})


class SeriesReaderProgress(Document):
    class_ = TextField('@class', default='SeriesReaderProgress')
    user_id = TextField()
    series_id = TextField()
    volume_id = TextField()
    page_number = IntegerField()
    last_updated = DateTimeField()

    @classmethod
    def save_for_user(cls, db, user_id, series_id, volume_id, page_number):
        doc = cls(
            _id='progress:{}:{}:{}'.format(user_id, series_id, volume_id),
            user_id=user_id,
            series_id=series_id,
            volume_id=volume_id,
            page_number=page_number,
            last_updated=datetime.utcnow(),
        )
        doc.store(db)
        cls.by_series.sync(db)

    @classmethod
    def retrieve_for_user(cls, db, user_id, series_id, limit=50):
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
