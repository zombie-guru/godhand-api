from .auth import AntiForgeryToken  # noqa
from .bookmark import Bookmark
from .series import Series
from .subscription import Subscription
from .user import UserSettings
from .volume import Volume


def init_views(db):
    Bookmark.sync(db)
    Series.sync(db)
    Subscription.sync(db)
    UserSettings.owner_by_subscriber.sync(db)
    Volume.sync(db)
