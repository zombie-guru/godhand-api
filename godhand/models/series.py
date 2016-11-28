from datetime import datetime

from couchdb.mapping import DateTimeField
from couchdb.mapping import Document
from couchdb.mapping import DictField
from couchdb.mapping import IntegerField
from couchdb.mapping import ListField
from couchdb.mapping import Mapping
from couchdb.mapping import TextField
from couchdb.mapping import ViewField
import couchdb.http

from .volume import Volume


class Series(Document):
    class_ = TextField('@class', default='Series')
    name = TextField()
    description = TextField()
    author = TextField()
    magazine = TextField()
    number_of_volumes = IntegerField()
    genres = ListField(TextField())
    cover_page = DictField(Mapping.build(
        volume_id=TextField(),
        page_number=IntegerField(),
    ))
    volumes_meta = ListField(DictField(Mapping.build(
        id=TextField(),
        language=TextField(),
        volume_number=IntegerField(),
    )))

    by_owner = ViewField('by_owner', '''
    function(doc) {
        if (doc['@class'] == 'Series')
    }
    ''')

    by_attribute = ViewField('by_attribute', '''
    function(doc) {
        if (doc['@class'] === 'Series') {
            var name = doc.name.toLowerCase();
            var hasVolumes = doc.volumes_meta.length > 0;
            emit([null, 'name:' + name], doc);
            emit([hasVolumes, 'name:' + name], doc);

            const languages = doc.volumes_meta
                .map(function(meta){
                    return meta.language;
                })
                .filter(function(value){
                    return !!value;
                })
                .reduce(function(agg, value) {
                    agg[value] = true;
                    return agg
                }, {});

            for (var language in languages) {
                emit(['lang:' + language, 'name:' + name], doc);
            }

            doc.genres.map(function(genre) {
                genre = genre.toLowerCase();
                emit([null, 'genre:' + genre, name], doc);
                emit([hasVolumes, 'genre:' + genre, name], doc);
            })
        }
    }
    ''')

    @classmethod
    def create(cls, db, **kws):
        doc = cls(**kws)
        doc.store(db)
        Series.by_attribute.sync(db)
        return doc

    @classmethod
    def get_series_for_user(cls, db, user_id):
        pass

    @classmethod
    def query(cls, db, genre=None, name=None, include_empty=False,
              full_match=False, language=None):
        if genre is not None and name is not None:
            raise ValueError('Only genre or name can be supplied')
        kws = {
            'startkey': [None if include_empty else True],
            'endkey': [None if include_empty else True],
            'limit': 50,
        }
        if language:
            kws['startkey'] = ['lang:{}'.format(language)]
            kws['endkey'] = ['lang:{}'.format(language)]
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

    def delete_volume(self, db, volume):
        self.volumes_meta = filter(
            lambda x: x.id != volume.id,
            self.volumes_meta)
        self.store(db)
        self.by_attribute.sync(db)

    def get_volumes_and_progress(self, db, user_id, language=None):
        """
        Mult-sort by the following attributes.

        1. All pages read go last.
        2. Partially read pages go first.
        3. Otherwise, sort by volume_number.
        """
        progress = SeriesReaderProgress.retrieve_for_user(db, user_id, self.id)
        progress = {x.volume_id: x.as_dict()for x in progress}
        volumes = Volume.collection_for_series(
            db, series_id=self.id, language=language)
        volumes = [
            dict(
                x.as_dict(short=True),
                progress=progress.get(x.id, None),
            )
            for x in volumes
        ]
        volumes.sort(key=lambda x: (
            x['progress']['page_number'] == x['pages'] - 1
            if x['progress'] else False,
            x['progress'] is None,
            x['volume_number'],
        ))
        return volumes

    def move_volume_to(self, db, series, volume):
        if volume.series_id != self.id:
            raise ValueError('{} not a volume of {}!'.format(
                volume.id, self.id))
        self.volumes_meta = filter(
            lambda x: x.id != volume.id,
            self.volumes_meta)
        series._update_volume_meta(volume)
        self.store(db)
        series.store(db)

    def update_volume_meta(self, db, volume):
        self._update_volume_meta(volume)
        self.store(db)

    def _update_volume_meta(self, volume):
        try:
            _volume = next(filter(
                lambda x: x.id == volume.id,
                self.volumes_meta))
            _volume['id'] = volume.id
            _volume['language'] = volume.language
            _volume['volume_number'] = volume.volume_number
        except StopIteration:
            self.volumes_meta.append({
                'id': volume.id,
                'language': volume.language,
                'volume_number': volume.volume_number,
            })

    def as_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'genres': self.genres,
            'author': self.author,
            'cover_page': {
                'page_number': self.cover_page.page_number,
                'volume_id': self.cover_page.volume_id,
            },
            'magazine': self.magazine,
            'number_of_volumes': self.number_of_volumes,
        }


class SeriesReaderProgress(Document):
    class_ = TextField('@class', default='SeriesReaderProgress')
    user_id = TextField()
    series_id = TextField()
    volume_id = TextField()
    page_number = IntegerField()
    max_spread = IntegerField()
    number_of_pages = IntegerField()
    last_updated = DateTimeField()
    series_name = TextField()
    volume_number = IntegerField()

    @classmethod
    def save_for_user(cls, db, user_id, series_id, volume, page_number):
        id = 'progress:{}:{}'.format(volume.id, user_id)
        doc = cls.load(db, id)
        if doc is None:
            doc = cls(id=id)
        series = Series.load(db, series_id)
        doc.user_id = user_id
        doc.series_id = series_id
        doc.volume_id = volume.id
        doc.page_number = page_number
        doc.last_updated = datetime.utcnow()
        doc.max_spread = volume.get_max_spread(page_number)
        doc.volume_number = volume.volume_number
        doc.number_of_pages = len(volume.pages)
        doc.series_name = series.name
        doc.store(db)
        cls.by_series.sync(db)
        cls.by_last_read.sync(db)

    @classmethod
    def retrieve_for_user(cls, db, user_id, series_id=None, limit=50):
        if series_id:
            try:
                return cls.by_series(
                    db,
                    startkey=[user_id, series_id, {}],
                    endkey=[user_id, series_id, None],
                    descending=True,
                    limit=limit,
                ).rows
            except couchdb.http.ResourceNotFound:
                return []
        else:
            try:
                return cls.by_last_read(
                    db,
                    startkey=[user_id, {}],
                    endkey=[user_id, None],
                    descending=True,
                    limit=limit,
                ).rows
            except couchdb.http.ResourceNotFound:
                return []

    by_series = ViewField('progress_by_series', '''
    function(doc) {
        if (doc['@class'] === 'SeriesReaderProgress') {
            emit(
                [
                    doc.user_id,
                    doc.series_id,
                    doc.last_updated
                ],
                doc
            );
        }
    }
    ''')

    by_last_read = ViewField('by_last_read', '''
    function(doc) {
        if (doc['@class'] === 'SeriesReaderProgress') {
            emit(
                [
                    doc.user_id,
                    doc.last_updated,
                ],
                doc
            );
        }
    }
    ''')

    def as_dict(self):
        return {
            'user_id': self.user_id,
            'series_id': self.series_id,
            'volume_id': self.volume_id,
            'max_spread': self.max_spread or 1,
            'number_of_pages': self.number_of_pages or 1000,
            'page_number': self.page_number,
            'last_updated': self.last_updated.isoformat(),
            'series_name': self.series_name,
            'volume_number': self.volume_number,
        }
