from functools import partial

from cornice import Service
from pyramid.security import Allow
from pyramid.security import Authenticated
import colander as co
import pycountry

from godhand.models import Series
from godhand.models import Subscription
from godhand.models import Volume


def owner_group(owner_id):
    return 'owner:{}'.format(owner_id)


def subscription_group(publisher_id):
    return 'subscription:{}'.format(publisher_id)


def groupfinder(userid, request):
    subscriptions = Subscription.query(
        request.registry['godhand:db'], subscriber_id=userid)
    return [
        owner_group(userid)
    ] + [
        subscription_group(x.publisher_id) for x in subscriptions
    ]


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
