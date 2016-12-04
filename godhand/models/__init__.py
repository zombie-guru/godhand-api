from .series import Series
from .series import SeriesReaderProgress
from .series import VolumeCollection
from .user import UserSettings
from .volume import Volume


def init_views(db):
    Series.by_name.sync(db)
    SeriesReaderProgress.by_last_read.sync(db)
    SeriesReaderProgress.by_series.sync(db)
    UserSettings.owner_by_subscriber.sync(db)
    Volume.by_series.sync(db)
    Volume.user_usage.sync(db)
    VolumeCollection.by_owner_name.sync(db)
