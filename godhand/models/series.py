from couchdb.mapping import IntegerField
from couchdb.mapping import ListField
from couchdb.mapping import TextField
from couchdb.mapping import ViewField

from .utils import GodhandDocument


class Series(GodhandDocument):
    """ Represents a collection of Volume objects.

    # Owner
    if ``owner_id`` is set, that means it belongs to a user. This has the
    property that.

    1. It should be uploadable but only by the owner.
    2. Owner can edit meta data fo this series.

    """
    class_ = TextField('@class', default='Series')
    name = TextField()
    description = TextField()
    author = TextField()
    magazine = TextField()
    number_of_volumes = IntegerField()
    genres = ListField(TextField())
    owner_id = TextField(default='root')

    def as_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'genres': self.genres,
            'author': self.author,
            'magazine': self.magazine,
            'number_of_volumes': self.number_of_volumes,
        }

    @classmethod
    def sync(cls, db):
        cls.by_owner_name.sync(db)

    @classmethod
    def create(cls, db, *, id=None, **kws):
        if not id:
            id = cls.generate_id()
        doc = cls(id=id, **kws)
        doc.store(db)
        cls.sync(db)
        return doc

    by_owner_name = ViewField('series-by-name', '''
    function(doc) {
        if (doc['@class'] === 'Series') {
            emit([doc.owner_id, doc.name.toLowerCase()], {_id: doc.id});
        }
    }
    ''')

    @classmethod
    def query(cls, db, owner_id='root', name_q=None, include_docs=True):
        if name_q:
            startkey = [owner_id, name_q.lower()]
            endkey = [owner_id, name_q.lower() + cls.MAX_STRING]
        else:
            startkey = [owner_id]
            endkey = [owner_id, {}]
        return cls.by_owner_name(
            db, startkey=startkey, endkey=endkey, include_docs=include_docs)

    def _key(self, owner_id):
        return '{}:{}'.format(self.id, owner_id)

    def retrieve_owner_instance(self, db, owner_id):
        if self.owner_id != owner_id:
            key = self._key(owner_id)
            db.copy(self.id, key)
            instance = Series.load(db, key)
            instance.owner_id = owner_id
            instance.store(db)
            return instance
        return self

    def user_can_view(self, owner_id):
        return self.owner_id == 'root' or owner_id == self.owner_id

    def add_volume(self, db, owner_id, volume):
        instance = self.retrieve_owner_instance(db, owner_id)
        volume.set_volume_collection(db, instance)
