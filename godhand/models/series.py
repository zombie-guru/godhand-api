from couchdb.mapping import Document
from couchdb.mapping import DictField
from couchdb.mapping import IntegerField
from couchdb.mapping import ListField
from couchdb.mapping import Mapping
from couchdb.mapping import TextField


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

    def add_volume(self, volume):
        self.volumes.append(
            {'id': volume.id, 'volume_number': volume.volume_number})


class SeriesReaderProgress(Document):
    class_ = TextField('@class', default='SeriesReaderProgress')
    volume_number = IntegerField()
    page_number = IntegerField()

    @classmethod
    def create_key(cls, user_id, series_id):
        return 'progress:{}:{}'.format(user_id, series_id)
