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
    def retrieve_or_create(cls, db, email):
        user = cls.from_email(db, email)
        if user is None:
            user = User(id=cls._id_from_email(email), email=email, groups=[])
        return user

    @classmethod
    def update(cls, db, email, groups):
        user = cls.retrieve_or_create(db, email)
        user.groups = groups
        user.store(db)
        User.by_email.sync(db)
        return user

    @classmethod
    def append_groups(cls, db, email, groups):
        user = cls.retrieve_or_create(db, email)
        user.groups = sorted(set(user.groups + groups))
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

    @classmethod
    def query(cls, db):
        return User.by_email(db)

    @ViewField.define('by_email')
    def by_email(doc):
        if doc['@class'] == 'User':
            yield doc['email'], doc

    def as_dict(self):
        return {
            'email': self.email,
            'groups': self.groups,
        }
