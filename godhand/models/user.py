from couchdb.mapping import Document
from couchdb.mapping import ListField
from couchdb.mapping import TextField


class UserSettings(Document):
    class_ = TextField('@class', default='UserSettings')
    user_id = TextField()
    language = TextField()
    subscribers = ListField(TextField())

    @classmethod
    def for_user(cls, db, user_id):
        settings = UserSettings.load(db, user_id)
        if settings:
            return settings
        return UserSettings(id=user_id, user_id=user_id)

    def add_subscriber(self, db, subscriber):
        if subscriber.id not in self.subscribers:
            self.subscribers.append(subscriber.id)
            self.store(db)
