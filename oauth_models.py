# oauth_models.py - OAuth2 модели и сервер
from authlib.integrations.flask_oauth2 import AuthorizationServer, ResourceProtector
from authlib.oauth2.rfc6749 import grants
from authlib.oauth2.rfc6749.models import ClientMixin, AuthorizationCodeMixin, TokenMixin
from authlib.common.security import generate_token
from werkzeug.security import gen_salt
from flask import current_app
from datetime import datetime
import json


# Эти модели добавляем к основным в app.py

class OAuth2Client(db.Model, ClientMixin):
    """OAuth2 клиенты (другие приложения университета)"""
    __tablename__ = 'oauth2_client'

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(40), unique=True, nullable=False)
    client_secret = db.Column(db.String(120), nullable=False)
    client_name = db.Column(db.String(100), nullable=False)
    client_description = db.Column(db.Text)

    # OAuth2 параметры
    redirect_uris = db.Column(db.Text)  # разделенные пробелами
    default_scopes = db.Column(db.Text)  # разделенные пробелами

    # Мета-данные
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Методы для authlib
    def get_client_id(self):
        return self.client_id

    def get_default_redirect_uri(self):
        return self.redirect_uris.split()[0] if self.redirect_uris else None

    def get_allowed_scope(self, scope):
        if not scope:
            return ''
        allowed = set(self.default_scopes.split())
        scopes = set(scope.split())
        return ' '.join([s for s in scopes if s in allowed])

    def check_redirect_uri(self, redirect_uri):
        return redirect_uri in self.redirect_uris.split()

    def has_client_secret(self):
        return bool(self.client_secret)

    def check_client_secret(self, client_secret):
        return self.client_secret == client_secret

    def check_token_endpoint_auth_method(self, method):
        return method in ['client_secret_post', 'client_secret_basic']

    def check_response_type(self, response_type):
        return response_type == 'code'

    def check_grant_type(self, grant_type):
        return grant_type in ['authorization_code', 'refresh_token']


class OAuth2AuthorizationCode(db.Model, AuthorizationCodeMixin):
    """Временные коды авторизации"""
    __tablename__ = 'oauth2_code'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    code = db.Column(db.String(120), unique=True, nullable=False)
    client_id = db.Column(db.String(40), db.ForeignKey('oauth2_client.client_id', ondelete='CASCADE'))
    redirect_uri = db.Column(db.Text)
    response_type = db.Column(db.String(40))
    scope = db.Column(db.Text)
    nonce = db.Column(db.Text)
    auth_time = db.Column(db.Integer, nullable=False, default=lambda: int(datetime.utcnow().timestamp()))
    code_challenge = db.Column(db.Text)
    code_challenge_method = db.Column(db.String(48))

    user = db.relationship('User')
    client = db.relationship('OAuth2Client')

    def is_expired(self):
        return self.auth_time + 300 < datetime.utcnow().timestamp()  # 5 минут

    def get_redirect_uri(self):
        return self.redirect_uri

    def get_scope(self):
        return self.scope

    def get_auth_time(self):
        return self.auth_time


class OAuth2Token(db.Model, TokenMixin):
    """OAuth2 токены"""
    __tablename__ = 'oauth2_token'

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(40), db.ForeignKey('oauth2_client.client_id', ondelete='CASCADE'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))

    # Токены
    access_token = db.Column(db.String(255), unique=True, nullable=False)
    refresh_token = db.Column(db.String(255), unique=True)

    # Параметры
    token_type = db.Column(db.String(40))
    scope = db.Column(db.Text)
    issued_at = db.Column(db.Integer, nullable=False, default=lambda: int(datetime.utcnow().timestamp()))
    expires_in = db.Column(db.Integer, nullable=False, default=3600)  # 1 час

    user = db.relationship('User')
    client = db.relationship('OAuth2Client')

    def get_scope(self):
        return self.scope

    def get_expires_in(self):
        return self.expires_in

    def is_expired(self):
        return self.issued_at + self.expires_in < datetime.utcnow().timestamp()


# Функции для OAuth2 сервера
def query_client(client_id):
    return OAuth2Client.query.filter_by(client_id=client_id).first()


def save_authorization_code(code, request, *args, **kwargs):
    nonce = request.data.get('nonce')
    code_challenge = request.data.get('code_challenge')
    code_challenge_method = request.data.get('code_challenge_method')

    auth_code = OAuth2AuthorizationCode(
        code=code,
        client_id=request.client.client_id,
        redirect_uri=request.redirect_uri,
        scope=request.scope,
        user_id=request.user.id,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        nonce=nonce,
    )
    db.session.add(auth_code)
    db.session.commit()
    return auth_code


def query_authorization_code(code, client):
    auth_code = OAuth2AuthorizationCode.query.filter_by(
        code=code, client_id=client.client_id).first()
    if auth_code and not auth_code.is_expired():
        return auth_code


def delete_authorization_code(authorization_code):
    db.session.delete(authorization_code)
    db.session.commit()


def save_bearer_token(token, request, *args, **kwargs):
    if request.user:
        oauth_token = OAuth2Token(
            client_id=request.client.client_id,
            user_id=request.user.id,
            **token
        )
        db.session.add(oauth_token)
        db.session.commit()


# Классы грантов
class AuthorizationCodeGrant(grants.AuthorizationCodeGrant):
    def create_authorization_code(self, client, grant_user, request):
        code = generate_token(48)
        save_authorization_code(code, request, client=client, grant_user=grant_user)
        return code

    def parse_authorization_code(self, code, client):
        return query_authorization_code(code, client)

    def delete_authorization_code(self, authorization_code):
        delete_authorization_code(authorization_code)

    def authenticate_user(self, authorization_code):
        return authorization_code.user


class RefreshTokenGrant(grants.RefreshTokenGrant):
    def authenticate_refresh_token(self, refresh_token):
        token = OAuth2Token.query.filter_by(refresh_token=refresh_token).first()
        if token and not token.is_expired():
            return token

    def authenticate_user(self, credential):
        return credential.user

    def revoke_old_credential(self, credential):
        db.session.delete(credential)
        db.session.commit()


# Инициализация OAuth2 сервера
authorization = AuthorizationServer()
require_oauth = ResourceProtector()


def config_oauth(app, db_instance):
    global db
    db = db_instance

    authorization.init_app(app, query_client=query_client, save_token=save_bearer_token)
    authorization.register_grant(AuthorizationCodeGrant)
    authorization.register_grant(RefreshTokenGrant)

    # Resource protector
    require_oauth.init_app(app)

    def query_token(access_token):
        return OAuth2Token.query.filter_by(access_token=access_token).first()

    require_oauth.register_token_validator(query_token)