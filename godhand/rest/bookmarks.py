from ..models import Bookmark
from .utils import GodhandService


bookmarks = GodhandService(
    name='bookmarks',
    path='/bookmarks',
)


@bookmarks.get()
def get_bookmarks(request):
    rows = Bookmark.query(
        request.registry['godhand:db'], user_id=request.authenticated_userid)
    return {'items': [x.as_dict() for x in rows]}
