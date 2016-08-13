import hashlib
import os

from oauth2client import client
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPUnauthorized
from pyramid.httpexceptions import HTTPNotFound
from pyramid.security import forget
from pyramid.security import remember
import colander as co
import requests

from ..models.auth import AntiForgeryToken
from ..models.auth import User
from .utils import GodhandService


class PermissionPathSchema(co.MappingSchema):
    permission = co.SchemaNode(
        co.String(), location='path', validator=co.OneOf(['view', 'write']))


class UserPathSchema(co.MappingSchema):
    userid = co.SchemaNode(co.String(), location='path', validator=co.Email())


user = GodhandService(
    name='user',
    path='/users/{userid}',
    permission='admin',
)
logout = GodhandService(
    name='logout',
    path='/logout',
    permission='authenticate',
)
permission_test = GodhandService(
    name='permission_check',
    path='/permissions/{permission}/test',
    permission='authenticate',
    schema=PermissionPathSchema,
    description='''
    Test if current user a permission.

    Useful for auth_request in nginx.
    '''
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


class UpdateUserSchema(UserPathSchema):
    @co.instantiate(missing=('user',))
    class groups(co.SequenceSchema):
        group = co.SchemaNode(co.String())


@user.get(schema=UserPathSchema)
def get_user(request):
    authdb = request.registry['godhand:authdb']
    userid = request.validated['userid']
    user = User.load(authdb, 'user:{}'.format(userid))
    if not user:
        raise HTTPNotFound()
    return dict(user.items())


@user.put(schema=UpdateUserSchema)
def update_user(request):
    authdb = request.registry['godhand:authdb']
    userid = request.validated['userid']
    groups = request.validated['groups']
    user = User.load(authdb, 'user:{}'.format(userid))
    if user is None:
        user = User(
            email=userid,
            id='user:{}'.format(userid),
        )
    user.groups = groups
    user.store(authdb)
    User.by_email.sync(authdb)


@user.delete(schema=UserPathSchema)
def delete_user(request):
    authdb = request.registry['godhand:authdb']
    userid = request.validated['userid']
    user = User.load(authdb, 'user:{}'.format(userid))
    if user:
        authdb.delete(user)


@logout.post()
def user_logout(request):
    response = request.response
    response.headers.extend(forget(request))
    return response


@permission_test.get()
def test_permission(request):
    v = request.validated
    if not request.has_permission(v['permission']):
        raise HTTPForbidden()
    return request.response


def create_anti_forgery_token():
    return 'token:' + hashlib.sha256(os.urandom(1024)).hexdigest()


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
