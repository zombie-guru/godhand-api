import colander as co

from ..models.user import UserSettings
from .utils import GodhandService
from .utils import language_validator


settings = GodhandService(
    name='settings',
    path='/settings',
    permission='view'
)


@settings.get()
def get_settings(request):
    settings = UserSettings.for_user(
        request.registry['godhand:db'], request.authenticated_userid)
    return {
        'user_id': settings.user_id,
        'language': settings.language,
    }


class PutSettingsSchema(co.MappingSchema):
    language = co.SchemaNode(
        co.String(), validator=language_validator, missing=None)


@settings.put(schema=PutSettingsSchema)
def put_settings(request):
    db = request.registry['godhand:db']
    settings = UserSettings.for_user(db, request.authenticated_userid)
    for key in ('language',):
        value = request.validated[key]
        if value:
            settings[key] = value
    settings.store(db)
