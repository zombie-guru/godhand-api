from .bookmark import Bookmark
from .series import Series
from .user import UserSettings
from .volume import Volume


def init_views(db):
    Bookmark.sync(db)
    Series.sync(db)
    UserSettings.owner_by_subscriber.sync(db)
    Volume.sync(db)
