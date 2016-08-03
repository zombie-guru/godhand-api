from couchdb.mapping import Document
from couchdb.mapping import DictField
from couchdb.mapping import IntegerField
from couchdb.mapping import ListField
from couchdb.mapping import Mapping
from couchdb.mapping import TextField
from couchdb.mapping import ViewField


def sync(db):
    Series.by_id.sync(db)


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

    by_id = ViewField('series', '''
        function(doc) {
            if ( doc['@class'] === 'Series') {
                emit(doc.id, doc);
            }
        }
    ''')

    def add_volume(self, volume):
        self.volumes.append(
            {'id': volume.id, 'volume_number': volume.volume_number})
