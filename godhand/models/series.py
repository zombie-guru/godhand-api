from couchdb.mapping import Document
from couchdb.mapping import DictField
from couchdb.mapping import IntegerField
from couchdb.mapping import ListField
from couchdb.mapping import Mapping
from couchdb.mapping import TextField
from couchdb.mapping import ViewField


class Series(Document):
    class_ = TextField('@class', default='Series')
    name = TextField()
    description = TextField()
    author = TextField()
    magazine = TextField()
    number_of_volumes = IntegerField()
    genres = ListField(TextField())
    volumes = ListField(DictField(Mapping.build(
        id=TextField(),
        volume_number=IntegerField(),
    )))

    by_meta = ViewField('by_meta', '''
    function(doc) {
        if ((doc['@class'] === 'Series') && (doc.volumes.length > 0)) {
            emit([doc.name], {'field': 'Series', 'value': doc.name});
            doc.genres.map(function(genre) {
                emit([genre], {'field': 'Genre', 'value': genre});
            });
        }
    }
    ''')

    by_genre = ViewField('by_genre', '''
    function(doc) {
        if ((doc['@class'] === 'Genre') && (doc.volumes.length > 0)) {
            doc.genres.map(function(genre) {
                emit([genre], doc);
            });
        }
    }
    ''')

    by_series = ViewField('by_series', '''
    function(doc) {
        if ((doc['@class'] === 'Series') && (doc.volumes.length > 0)) {
            emit([doc.name], doc);
        }
    }
    ''')

    def add_volume(self, volume):
        self.volumes.append(
            {'id': volume.id, 'volume_number': volume.volume_number})


class SeriesReaderProgress(Document):
    class_ = TextField('@class', default='SeriesReaderProgress')
    volume_number = IntegerField()
    page_number = IntegerField()

    @classmethod
    def create_key(cls, user_id, series_id):
        return 'progress:{}:{}'.format(user_id, series_id)
