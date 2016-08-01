from couchdb.mapping import Document
from couchdb.mapping import IntegerField
from couchdb.mapping import ListField
from couchdb.mapping import TextField
from couchdb.mapping import ViewField


def sync(db):
    Series.by_id.sync(db)
    Series.by_id_has_volumes.sync(db)


class Series(Document):
    name = TextField()
    description = TextField()
    author = TextField()
    magazine = TextField()
    number_of_volumes = IntegerField()
    genres = ListField(TextField())
    volumes = ListField(TextField())

    by_id = ViewField('series', '''
        function(doc) {
            emit(doc.id, doc);
        }
    ''')

    by_id_has_volumes = ViewField('series', '''
        function(doc) {
            if ( doc.volumes.length > 0 ) {
                emit(doc.id, doc);
            }
        }
    ''')
