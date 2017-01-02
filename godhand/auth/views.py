import hashlib
import os

from cornice import Service
from oauth2client import client
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPUnauthorized
from pyramid.httpexceptions import HTTPSeeOther
from pyramid.security import forget
from pyramid.security import remember
import colander as co
import requests

from .models import AntiForgeryToken


logout = Service(
    name='logout',
    path='/logout',
    permission=None,
)
oauth2_init = Service(
    name='oauth2-init',
    path='/oauth2-init',
    permission=None,
)
oauth2_callback = Service(
    name='oauth2-callback',
    path='/oauth2-callback',
    permission=None,
)


@logout.post()
def user_logout(request):
    """ Logout user.
    """
    response = request.response
    response.headers.extend(forget(request))
    return response


def create_anti_forgery_token():
    return 'token:' + hashlib.sha256(os.urandom(1024)).hexdigest()


class InitOauth2Schema(co.MappingSchema):
    callback_url = co.SchemaNode(
        co.String(), location='querystring', validator=co.url)
    error_callback_url = co.SchemaNode(
        co.String(), location='querystring', validator=co.url)


@oauth2_init.get(schema=InitOauth2Schema)
def init_oauth2(request):
    """ Redirect user to this URL to start OAuth process.
    """
    v = request.validated
    email = request.unauthenticated_userid or ''
    token = AntiForgeryToken(id=create_anti_forgery_token(), **v)
    token.store(request.registry['godhand:authdb'])
    cfg = request.registry['godhand:cfg']
    query = {
        'client_id': cfg.google_client_id,
        'state': token.id,
        'application_name': cfg.google_client_appname,
        'scope': 'openid email',
        'redirect_uri': request.route_url('oauth2-callback'),
        'login_hint': email,
        'response_type': 'code',
    }
    return HTTPFound(request.route_url('google-oauth2', _query=query))


class VerifyOAuthTokenSchema(co.MappingSchema):
    state = co.SchemaNode(co.String(), location='querystring')
    code = co.SchemaNode(co.String(), location='querystring')


@oauth2_callback.get(schema=VerifyOAuthTokenSchema)
def verify_oauth2_token(request):
    """ OAuth provider should redirect user to this endpoint.
    """
    authdb = request.registry['godhand:authdb']
    cfg = request.registry['godhand:cfg']
    # validate anti-forgery token
    token = AntiForgeryToken.load(authdb, request.validated['state'])
    if token is None:
        raise HTTPUnauthorized(
            'Callback must be initialized from /oauth2-init')
    else:
        authdb.delete(token)
    # validate code sent by client with google
    r = requests.post(
        'https://www.googleapis.com/oauth2/v4/token',
        data={
            'code': request.validated['code'],
            'state': request.validated['state'],
            'client_id': cfg.google_client_id,
            'client_secret': cfg.google_client_secret,
            'redirect_uri': request.route_url('oauth2-callback'),
            'grant_type': 'authorization_code',
        },
    )
    if r.status_code != 200:
        raise HTTPSeeOther(token.error_callback_url)
    info = r.json()
    login_info = client.verify_id_token(info['id_token'], cfg.google_client_id)
    if login_info['email_verified'] and login_info['email']:
        # if all is good, sign the cookie and send back to client
        response = request.response
        response.headers.extend(remember(request, login_info['email']))
        return HTTPFound(token.callback_url, headers=response.headers)
    else:
        raise HTTPSeeOther(token.error_callback_url)
