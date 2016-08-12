from datetime import datetime

from couchdb.mapping import Document
from couchdb.mapping import DateTimeField
from couchdb.mapping import ListField
from couchdb.mapping import TextField


class AntiForgeryToken(Document):
    class_ = TextField('@class', default='AntiForgeryToken')
    added = DateTimeField(default=datetime.now)


class User(Document):
    class_ = TextField('User', default='User')
    email = TextField()
    groups = ListField(TextField())
