from datetime import datetime
from datetime import timedelta
import hashlib
import jwt
import os

from oauth2client import client
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.httpexceptions import HTTPConflict
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPUnauthorized
from pyramid.httpexceptions import HTTPNotFound
from pyramid.httpexceptions import HTTPSeeOther
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


users = GodhandService(
    name='users',
    path='/users',
    permission='admin'
)
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
permissions = GodhandService(
    name='permissions',
    path='/permissions',
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
oauth2_init = GodhandService(
    name='oauth2-init',
    path='/oauth2-init',
    permission='authenticate',
)
oauth2_callback = GodhandService(
    name='oauth2-callback',
    path='/oauth2-callback',
    permission='authenticate',
)
create_signup_token = GodhandService(
    name='create-signup-token',
    path='/create-signup-token',
    permission='admin',
    description='Generate tokens with which users can signup for access.'
)
use_signup_token = GodhandService(
    name='use-signup-token',
    path='/use-signup-token',
    permission='authenticate',
    description='Use generated signup tokens.'
)


class GetUsersSchema(co.MappingSchema):
    pass


@users.get(schema=GetUsersSchema)
def get_users(request):
    users = User.query(request.registry['godhand:authdb'])
    return {'items': [x.as_dict() for x in users]}


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
    return dict(user.as_dict())


@user.put(schema=UpdateUserSchema)
def update_user(request):
    authdb = request.registry['godhand:authdb']
    userid = request.validated['userid']
    groups = request.validated['groups']
    User.update(authdb, userid, groups)


@user.delete(schema=UserPathSchema)
def delete_user(request):
    authdb = request.registry['godhand:authdb']
    userid = request.validated['userid']
    User.delete(authdb, userid)


@logout.post()
def user_logout(request):
    response = request.response
    response.headers.extend(forget(request))
    return response


@permissions.get()
def get_permissions(request):
    logged_in = request.authenticated_userid is not None
    auth_disabled = request.registry['godhand:cfg'].disable_auth
    return {
        'needs_authentication': not auth_disabled and not logged_in,
        'permissions': {
            k: bool(request.has_permission(k))
            for k in ('view', 'write', 'admin')
        },
    }


@permission_test.get()
def test_permission(request):
    v = request.validated
    if not request.has_permission(v['permission']):
        raise HTTPForbidden()
    return request.response


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


def get_signup_token_secret(request):
    secret = request.registry['godhand:cfg'].token_secret
    if secret is None:
        raise HTTPConflict('No token secret has been configured.')
    return secret


class CreateSignupTokenSchema(co.MappingSchema):
    expiration_time = co.SchemaNode(
        co.Integer(),
        location='body',
        default=timedelta(days=1).total_seconds(),
        description='Time that token is valid for.',
    )

    @co.instantiate(location='body', validator=co.Length(min=1))
    class groups(co.SequenceSchema):
        group = co.SchemaNode(
            co.String(),
            validator=co.OneOf(['user', 'admin']),
        )


@create_signup_token.post(
    accept='application/jwt',
    schema=CreateSignupTokenSchema,
)
def post_create_signup_token(request):
    """ Create a signup token for someone to use.

    Raises 409 conflict if token secret has not been configured.
    """
    secret = get_signup_token_secret(request)
    now = datetime.utcnow()
    response = request.response
    response.body = jwt.encode({
        'exp': now + timedelta(seconds=request.validated['expiration_time']),
        'iat': now,
        'groups': request.validated['groups'],
    }, secret, algorithm='HS256')
    response.content_type = 'application/jwt'
    return response


@use_signup_token.post(
    content_type='application/jwt',
)
def post_use_signup_token(request):
    if request.authenticated_userid is None:
        raise HTTPUnauthorized()
    secret = get_signup_token_secret(request)
    try:
        groups = jwt.decode(request.body, secret)['groups']
    except jwt.InvalidIssuedAtError:
        HTTPBadRequest('Token is created in the future.')
    except jwt.ExpiredSignatureError:
        HTTPBadRequest('Token is expired.')
    authdb = request.registry['godhand:authdb']
    User.append_groups(authdb, request.authenticated_userid, groups)
