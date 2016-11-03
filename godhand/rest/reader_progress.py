import colander as co

from ..models.series import SeriesReaderProgress
from .utils import GodhandService
from .utils import ValidatedVolume


class VolumePathSchema(co.MappingSchema):
    volume = co.SchemaNode(
        ValidatedVolume(), location='path', validator=co.NoneOf([None]))


class VolumePagePathSchema(VolumePathSchema):
    page = co.SchemaNode(co.Integer(), location='path')


reader_progress = GodhandService(
    name='reader_progress',
    path='/reader_progress'
)


@reader_progress.get(
    permission='view',
)
def get_reader_progress(request):
    """ Get latest progress for each series.
    """
    items = SeriesReaderProgress.retrieve_for_user(
        request.registry['godhand:db'], user_id=request.authenticated_userid)
    return {'items': [x.as_dict() for x in items]}
