from functools import partial

from cornice import Service
from pyramid.security import Allow
from pyramid.security import Authenticated
import colander as co
import pycountry

from godhand.models.series import Series
from godhand.models.volume import Volume


def groupfinder(userid, request):
    return [userid]


default_acl = (
    (Allow, Authenticated, 'info'),
)


GodhandService = partial(
    Service,
    acl=lambda r: default_acl,
    permission='info',
)


class ValidatedSeries(co.String):
    def deserialize(self, node, cstruct):
        appstruct = super(ValidatedSeries, self).deserialize(node, cstruct)
        db = node.bindings['request'].registry['godhand:db']
        return Series.load(db, appstruct)


class ValidatedVolume(co.String):
    def deserialize(self, node, cstruct):
        appstruct = super(ValidatedVolume, self).deserialize(node, cstruct)
        db = node.bindings['request'].registry['godhand:db']
        return Volume.load(db, appstruct)


def language_validator(node, cstruct):
    try:
        pycountry.languages.get(iso639_3_code=cstruct)
    except KeyError:
        raise co.Invalid(node, 'Invalid ISO639-3 code.')
