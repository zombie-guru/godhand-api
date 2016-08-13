import hashlib
import os

from oauth2client import client
from pyramid.httpexceptions import HTTPUnauthorized
from pyramid.security import remember
import colander as co
import requests

from ..models.auth import AntiForgeryToken
from .utils import GodhandService

user = GodhandService(
    name='user',
    path='/user',
    permission='authenticate',
)
oauth_init = GodhandService(
    name='oauth-init',
    path='/oauth-init',
    permission='authenticate',
)
oauth_callback = GodhandService(
    name='oauth-callback',
    path='/oauth-callback',
    permission='authenticate',
)


def create_anti_forgery_token():
    return 'token:' + hashlib.sha256(os.urandom(1024)).hexdigest()


@user.get()
def get_user(request):
    """ Get logged in user information.
    """
    return {'email': request.unauthenticated_userid}


@oauth_init.get()
def init_oauth(request):
    """ Redirect user to this URL to start OAuth process.
    """
    email = request.unauthenticated_userid or ''
    token = AntiForgeryToken(id=create_anti_forgery_token())
    token.store(request.registry['godhand:authdb'])
    cfg = request.registry['godhand:cfg']
    return {
        'client_id': cfg.google_client_id,
        'state': token.id,
        'application_name': cfg.google_client_appname,
        'scope': 'openid email',
        'redirect_uri': request.route_url('oauth-callback'),
        'login_hint': email,
    }


class VerifyOAuthTokenSchema(co.MappingSchema):
    state = co.SchemaNode(co.String(), location='querystring')
    code = co.SchemaNode(co.String(), location='querystring')


@oauth_callback.get(schema=VerifyOAuthTokenSchema)
def verify_oauth_token(request):
    """ OAuth provider should redirect user to this endpoint.
    """
    authdb = request.registry['godhand:authdb']
    cfg = request.registry['godhand:cfg']
    # validate anti-forgery token
    token = AntiForgeryToken.load(authdb, request.validated['state'])
    if token is None:
        raise HTTPUnauthorized()
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
            'redirect_uri': request.route_url('oauth-callback'),
            'grant_type': 'authorization_code',
        },
    )
    if r.status_code != 200:
        raise HTTPUnauthorized()
    info = r.json()
    login_info = client.verify_id_token(info['id_token'], cfg.google_client_id)
    if login_info['email_verified'] and login_info['email']:
        # if all is good, sign the cookie and send back to client
        response = request.response
        response.headers.extend(remember(request, login_info['email']))
        return {'email': login_info['email']}
    else:
        raise HTTPUnauthorized()
