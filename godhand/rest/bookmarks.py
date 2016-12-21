from ..models import Bookmark
from .utils import GodhandService


bookmarks = GodhandService(
    name='bookmarks',
    path='/bookmarks',
)


@bookmarks.get()
def get_bookmarks(request):
    """ Get bookmarks for logged in user.

    .. code-block:: js

        {
            "series_id": "series-abc",
            "volume_id": "volume-abc",
            "number_of_pages": 18,
            "page_number": 0,
            "last_updated": "2016-01-04 14:16:39.000",
            "volume_number": 8,
            "page0": "http://left.png",
            "page1": null
        }

    """
    rows = Bookmark.query(
        request.registry['godhand:db'], user_id=request.authenticated_userid)
    return {'items': [x.as_dict(request) for x in rows]}
