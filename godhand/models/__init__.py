from .series import Series  # noqa
from .series import SeriesReaderProgress  # noqa
from .volume import Volume  # noqa


def init_views(db):
    Volume.by_series.sync(db)
    Volume.summary_by_series.sync(db)
    Volume.user_usage.sync(db)
