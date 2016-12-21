from couchdb.mapping import Document
from couchdb.mapping import ListField
from couchdb.mapping import TextField
from couchdb.mapping import ViewField


class UserSettings(Document):
    class_ = TextField('@class', default='UserSettings')
    user_id = TextField()
    subscribers = ListField(TextField())

    owner_by_subscriber = ViewField('owner_by_subscriber', '''
    function(doc) {
        if (doc['@class'] === 'UserSettings') {
            doc.subscribers.forEach(function(subscriber) {
                emit([subscriber], doc.user_id);
            })
        }
    }
    ''', wrapper=lambda x: x['value'])

    @classmethod
    def for_user(cls, db, user_id):
        settings = UserSettings.load(db, user_id)
        if settings:
            return settings
        return UserSettings(id=user_id, user_id=user_id)

    @classmethod
    def get_subscribed_owner_ids(cls, db, subscriber_id):
        return cls.owner_by_subscriber(db, key=[subscriber_id]).rows

    def add_subscriber(self, db, subscriber_id):
        if subscriber_id not in self.subscribers:
            self.subscribers.append(subscriber_id)
            self.store(db)
            self.owner_by_subscriber.sync(db)

    def remove_subscriber(self, db, subscriber_id):
        if subscriber_id in self.subscribers:
            self.subscribers.remove(subscriber_id)
            self.store(db)
            self.owner_by_subscriber.sync(db)
