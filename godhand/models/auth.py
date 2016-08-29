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

    @classmethod
    def _id_from_email(cls, email):
        return 'user:{}'.format(email)

    @classmethod
    def update(cls, db, email, groups):
        user = cls.from_email(db, email)
        if user is None:
            user = User(email=email, id=cls._id_from_email(email))
        user.groups = groups
        user.store(db)
        User.by_email.sync(db)
        return user

    @classmethod
    def delete(cls, db, email):
        user = cls.from_email(db, email)
        if user:
            db.delete(user)
            User.by_email.sync(db)

    @classmethod
    def from_email(cls, db, email):
        return User.load(db, cls._id_from_email(email))

    by_email = ViewField('user_by_email', '''
    function(doc) {
        if (doc['@class'] == 'User') {
            emit(doc.email, doc);
        }
    }
    ''')
