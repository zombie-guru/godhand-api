from couchdb.mapping import IntegerField
from couchdb.mapping import TextField
from couchdb.mapping import ViewField

from .utils import GodhandDocument


class Subscription(GodhandDocument):
    CLEARED = 0
    ALLOWED = 1
    BLOCKED = 2

    @classmethod
    def map_status_str(cls, status):
        try:
            return {
                'block': cls.BLOCKED,
                'allow': cls.ALLOWED,
                'clear': cls.CLEARED,
            }[status]
        except KeyError:
            raise ValueError('Invalid status string: {}'.format(status))

    class_ = TextField('@class', default='Subscription')
    subscriber_id = TextField()
    subscriber_status = IntegerField(default=0)

    publisher_id = TextField()
    publisher_status = IntegerField(default=0)

    @classmethod
    def retrieve(cls, db, subscriber_id, publisher_id):
        key = 'subscription:{}:{}'.format(publisher_id, subscriber_id)
        instance = cls.load(db, key)
        if instance is None:
            instance = cls(
                id=key,
                subscriber_id=subscriber_id,
                publisher_id=publisher_id)
        return instance

    @classmethod
    def sync(cls, db):
        cls.by_publisher.sync(db)
        cls.by_subscriber.sync(db)

    by_publisher = ViewField('subscriptions-by-publisher', '''
    function(doc) {
        if (
            doc['@class'] == 'Subscription' &&
            (doc.subscriber_status === 1) &&
            (doc.publisher_status === 1)
        ) {
            emit([doc.publisher_id, doc.subscriber_id], {_id: doc.id});
        }
    }
    ''')

    by_subscriber = ViewField('subscriptions-by-subscriber', '''
    function(doc) {
        if (
            doc['@class'] == 'Subscription' &&
            doc.subscriber_status === 1 &&
            doc.publisher_status === 1
        ) {
            emit([doc.subscriber_id, doc.publisher_id], {_id: doc.id});
        }
    }
    ''')

    @classmethod
    def query(
            cls, db, subscriber_id=None, publisher_id=None, include_docs=True):
        if subscriber_id and publisher_id:
            raise ValueError('XOR(subscriber_id, publisher_id) only.')
        if subscriber_id:
            return cls.by_subscriber(
                db,
                startkey=[subscriber_id],
                endkey=[subscriber_id, {}],
                include_docs=include_docs)
        elif publisher_id:
            return cls.by_publisher(
                db,
                startkey=[publisher_id],
                endkey=[publisher_id, {}],
                include_docs=include_docs)
        raise ValueError('subscriber_id or publisher_id must be supplied.')

    requests_by_publisher = ViewField(
        'subscriptions-requests-by-publisher',
        '''
        function(doc) {
            if (
                doc.id.startsWith('subscription:') &&
                doc.subscriber_status === 1
                doc.publisher_status === 0
            ) {
                emit([doc.publisher_id, doc.subscriber_id], {_id: doc.id});
            }
        }
        ''')

    requests_by_subscriber = ViewField(
        'subscriptions-requests-by-subscriber', '''
        function(doc) {
            if (
                doc.id.startsWith('subscription:') &&
                doc.subscriber_status === 0
                doc.publisher_status === 1
            ) {
                emit([doc.subscriber_id, doc.publisher_id], {_id: doc.id});
            }
        }
        ''')

    @classmethod
    def query_requests(
            cls, db, subscriber_id=None, publisher_id=None, include_docs=True):
        if subscriber_id and publisher_id:
            raise ValueError('XOR(subscriber_id, publisher_id) only.')
        if subscriber_id:
            return cls.requests_by_subscriber(
                startkey=[subscriber_id],
                endkey=[subscriber_id, {}],
                include_docs=include_docs)
        elif publisher_id:
            return cls.requests_by_publisher(
                startkey=[publisher_id],
                endkey=[publisher_id, {}],
                include_docs=include_docs)
        raise ValueError('subscriber_id or publisher_id must be supplied.')

    def update_publisher_status(self, db, status):
        self.publisher_status = self.map_status_str(status)
        self.store(db)
        self.sync(db)

    def update_subscriber_status(self, db, status):
        self.subscriber_status = self.map_status_str(status)
        self.store(db)
        self.sync(db)

    def as_dict(self):
        return {
            'id': self.id,
            'subscriber_id': self.subscriber_id,
            'publisher_id': self.publisher_id,
        }
