from couchdb.mapping import Document
from couchdb.mapping import DictField
from couchdb.mapping import IntegerField
from couchdb.mapping import ListField
from couchdb.mapping import Mapping
from couchdb.mapping import TextField
from couchdb.mapping import ViewField


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

    search = ViewField('search', '''
    function(doc) {
        if (doc['@class'] === 'Series') {
            emit([null, doc.name, 'name'], 1);
            doc.genres.map(function(genre) {
                emit([null, genre, 'genres'], 1);
            });
            if (doc.volumes.length > 0) {
                emit([true, doc.name, 'name'], 1);
                doc.genres.map(function(genre) {
                    emit([true, genre, 'genres'], 1);
                });
            }
        }
    }
    ''', reduce_fun='_sum', wrapper=lambda x: {
        'attribute': x['key'][2],
        'value': x['key'][1],
        'matches': x['value'],
    })

    search_by_attribute = ViewField('search_by_attribute', '''
    function(doc) {
        if (doc['@class'] === 'Series') {
            emit([null, 'name', doc.name], 1);
            doc.genres.map(function(genre) {
                emit([null, 'genres', genre], 1);
            });
            if (doc.volumes.length > 0) {
                emit([true, 'name', doc.name], 1);
                doc.genres.map(function(genre) {
                    emit([true, 'genres', genre], 1);
                });
            }
        }
    }
    ''', reduce_fun='_sum', wrapper=lambda x: {
        'attribute': x['key'][1],
        'value': x['key'][2],
        'matches': x['value'],
    })

    by_attribute = ViewField('by_attribute', '''
    function(doc) {
        if (doc['@class'] === 'Series') {
            var name = doc.name.toLowerCase();
            emit([null, 'name:' + name], doc);
            emit([doc.volumes.length > 0, 'name:' + name], doc);
            doc.genres.map(function(genre) {
                genre = genre.toLowerCase();
                emit([null, 'genre:' + genre, name], doc);
                emit([doc.volumes.length > 0, 'genre:' + genre, name], doc);
            })
        }
    }
    ''')

    @classmethod
    def query(cls, db, genre=None, name=None, include_empty=False,
              full_match=False):
        if genre is not None and name is not None:
            raise ValueError('Only genre or name can be supplied')
        kws = {
            'startkey': [None if include_empty else True],
            'endkey': [None if include_empty else True],
            'limit': 50,
        }
        if genre:
            genre = genre.lower()
            kws['startkey'].extend(['genre:' + genre, None])
            if full_match:
                kws['endkey'].extend(['genre:' + genre, {}])
            else:
                kws['endkey'].extend([u'genre:' + genre + u'\ufff0'])
        elif name:
            name = name.lower()
            kws['startkey'].append('name:' + name)
            if full_match:
                kws['endkey'].append('name:' + name)
            else:
                kws['endkey'].append(u'name:' + name + u'\ufff0')
        else:
            kws['startkey'].append('name:')
            kws['endkey'].append(u'name:\ufff0')
        return Series.by_attribute(db, **kws)

    @classmethod
    def search_attributes(
            cls, db, attribute=None, query=None, include_empty=False):
        kws = {
            'startkey': [None if include_empty else True],
            'endkey': [None if include_empty else True],
            'limit': 50,
            'group': True,
        }
        if attribute:
            view = Series.search_by_attribute
            kws['startkey'].append(attribute)
            kws['endkey'].append(attribute)
        else:
            view = Series.search
        if query:
            kws['startkey'].append(query)
            kws['endkey'].append(query + u'\ufff0')
        else:
            kws['startkey'].append(None)
            kws['endkey'].append({})
        return view(db, **kws)

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
