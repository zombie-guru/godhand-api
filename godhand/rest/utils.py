from functools import partial

from cornice import Service
import colander as co
import pycountry

from godhand.models.auth import User
from godhand.models.series import Series
from godhand.models.volume import Volume


def groupfinder(userid, request):
    authdb = request.registry['godhand:authdb']
    user = User.by_email(authdb, key=userid, limit=1).rows
    if len(user) == 0:
        return []
    user = user[0]
    return [
        user.email,
    ] + ['group:{}'.format(x) for x in user.groups]


GodhandService = partial(Service)


class ValidatedSeries(co.String):
    def deserialize(self, node, cstruct):
        appstruct = super(ValidatedSeries, self).deserialize(node, cstruct)
        db = node.bindings['request'].registry['godhand:db']
        return Series.load(db, appstruct)


class ValidatedUser(co.String):
    def deserialize(self, node, cstruct):
        appstruct = super(ValidatedUser, self).deserialize(node, cstruct)
        db = node.bindings['request'].registry['godhand:db']
        return User.load(db, appstruct)


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
