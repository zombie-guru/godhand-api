from .series import Series  # noqa
from .series import SeriesReaderProgress  # noqa
from .user import UserSettings
from .volume import Volume


def init_views(db):
    UserSettings.owner_by_subscriber.sync(db)
    Volume.by_series.sync(db)
    Volume.summary_by_series.sync(db)
    Volume.user_usage.sync(db)
