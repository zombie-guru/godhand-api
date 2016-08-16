from datetime import datetime

from couchdb.mapping import Document
from couchdb.mapping import DateTimeField
from couchdb.mapping import ListField
from couchdb.mapping import TextField
from couchdb.mapping import ViewField


class AntiForgeryToken(Document):
    class_ = TextField('@class', default='AntiForgeryToken')
    added = DateTimeField(default=datetime.now)
    callback_url = TextField()
    error_callback_url = TextField()


class User(Document):
    class_ = TextField('@class', default='User')
    email = TextField()
    groups = ListField(TextField())

    by_email = ViewField('user_by_email', '''
    function(doc) {
        if (doc['@class'] == 'User') {
            emit(doc.email, doc);
        }
    }
    ''')
