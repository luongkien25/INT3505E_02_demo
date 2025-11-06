import os
import jwt
from uuid import uuid4
from functools import wraps
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, g, current_app, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth  
from extensions import db
from models import Customer, Role, RefreshToken

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

oauth = OAuth()

def init_authlib(app):
    """Khởi tạo OAuth client; cấu hình Google OIDC nếu có client_id/secret."""
    oauth.init_app(app)
    gid = app.config.get('OAUTH_GOOGLE_CLIENT_ID')
    gsecret = app.config.get('OAUTH_GOOGLE_CLIENT_SECRET')
    if gid and gsecret:
        oauth.register(
            name='google',
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_id=gid,
            client_secret=gsecret,
            client_kwargs={'scope': 'openid email profile'}  # OIDC scopes
        )

ROLE_SCOPES = {
    'admin': [
        'product:read', 'product:write',
        'order:read', 'order:write',
        'customer:read', 'customer:write'
    ],
    'user': [
        'product:read',
        'order:read', 'order:write'
    ],
}

def scopes_for(customer: Customer):
    names = [r.name for r in customer.roles]
    s = set()
    for n in names:
        s.update(ROLE_SCOPES.get(n, []))
    return sorted(s)

def _jwt_config():
    return (
        current_app.config['JWT_SECRET'],
        current_app.config.get('JWT_ALG', 'HS256'),
        current_app.config['ACCESS_TOKEN_EXPIRES'],
        current_app.config['REFRESH_TOKEN_EXPIRES']
    )

def create_access_token(customer: Customer):
    secret, alg, access_ttl, _ = _jwt_config()
    now = datetime.utcnow()
    payload = {
        'iss': 'shop-api',
        'sub': str(customer.id),
        'email': customer.email,
        'roles': [r.name for r in customer.roles],
        'scopes': scopes_for(customer),
        'iat': int(now.timestamp()),
        'exp': int((now + access_ttl).timestamp()),
        'jti': str(uuid4()),
        'type': 'access'
    }
    return jwt.encode(payload, secret, algorithm=alg)

def create_refresh_token(customer: Customer):
    secret, alg, _, refresh_ttl = _jwt_config()
    now = datetime.utcnow()
    jti = str(uuid4())
    payload = {
        'iss': 'shop-api',
        'sub': str(customer.id),
        'iat': int(now.timestamp()),
        'exp': int((now + refresh_ttl).timestamp()),
        'jti': jti,
        'type': 'refresh'
    }
    token = jwt.encode(payload, secret, algorithm=alg)
    db.session.add(RefreshToken(
        jti=jti, customer_id=customer.id, revoked=False,
        expires_at=now + refresh_ttl
    ))
    db.session.commit()
    return token

def decode_token(token: str):
    secret, alg, *_ = _jwt_config()
    return jwt.decode(token, secret, algorithms=[alg])

def auth_required(scopes=None, roles=None, allow_self=False, customer_id_param=None):
    scopes = set(scopes or [])
    roles = set(roles or [])

    def wrapper(fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            hdr = request.headers.get('Authorization', '')
            if not hdr.startswith('Bearer '):
                return jsonify({'message': 'Missing Authorization: Bearer <token>'}), 401
            token = hdr.split(' ', 1)[1].strip()
            try:
                payload = decode_token(token)
            except jwt.ExpiredSignatureError:
                return jsonify({'message': 'Access token expired'}), 401
            except Exception:
                return jsonify({'message': 'Invalid token'}), 401

            if payload.get('type') != 'access':
                return jsonify({'message': 'Use access token for this endpoint'}), 401

            g.current_token = payload
            g.current_user_id = int(payload['sub'])
            g.current_roles = set(payload.get('roles', []))
            g.current_scopes = set(payload.get('scopes', []))

            if roles and not (g.current_roles & roles):
                return jsonify({'message': 'Forbidden: missing required role'}), 403

            if scopes and not scopes.issubset(g.current_scopes):
                return jsonify({'message': 'Forbidden: missing required scope'}), 403

            if allow_self and customer_id_param:
                try:
                    target_id = int(kwargs.get(customer_id_param))
                except Exception:
                    target_id = None
                if (target_id is not None) and (target_id == g.current_user_id):
                    return fn(*args, **kwargs)
                if 'admin' not in g.current_roles:
                    return jsonify({'message': 'Forbidden: only owner or admin'}), 403

            return fn(*args, **kwargs)
        return inner
    return wrapper

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    for f in ('name', 'email', 'password'):
        if f not in data:
            return jsonify({'message': 'Missing name/email/password'}), 400
    if Customer.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'Email already exists'}), 409

    user = Customer(name=data['name'], email=data['email'])
    user.set_password(data['password'])

    # gán role mặc định 'user'
    role_user = Role.query.filter_by(name='user').first()
    if not role_user:
        role_user = Role(name='user')
        db.session.add(role_user)
    user.roles = [role_user]

    db.session.add(user)
    db.session.commit()

    return jsonify({'id': user.id, 'email': user.email}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    if 'email' not in data or 'password' not in data:
        return jsonify({'message': 'Missing email/password'}), 400

    user = Customer.query.filter_by(email=data['email']).first()
    if not user or not user.check_password(data['password']):
        return jsonify({'message': 'Invalid credentials'}), 401

    access = create_access_token(user)
    refresh = create_refresh_token(user)
    ttl = int(current_app.config['ACCESS_TOKEN_EXPIRES'].total_seconds())

    return jsonify({
        'token_type': 'Bearer',
        'access_token': access,
        'refresh_token': refresh,
        'expires_in': ttl,
        'user': {'id': user.id, 'email': user.email, 'roles': [r.name for r in user.roles], 'scopes': scopes_for(user)}
    }), 200

@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    data = request.get_json() or {}
    if 'refresh_token' not in data:
        return jsonify({'message': 'Missing refresh_token'}), 400
    try:
        payload = decode_token(data['refresh_token'])
    except jwt.ExpiredSignatureError:
        return jsonify({'message': 'Refresh token expired'}), 401
    except Exception:
        return jsonify({'message': 'Invalid refresh token'}), 401

    if payload.get('type') != 'refresh':
        return jsonify({'message': 'Not a refresh token'}), 400

    rt = RefreshToken.query.filter_by(jti=payload['jti'], customer_id=int(payload['sub'])).first()
    if not rt or rt.revoked or rt.expires_at < datetime.utcnow():
        return jsonify({'message': 'Refresh token not valid'}), 401

    user = Customer.query.get(rt.customer_id)
    rt.revoked = True
    db.session.commit()

    new_access = create_access_token(user)
    new_refresh = create_refresh_token(user)

    return jsonify({'access_token': new_access, 'refresh_token': new_refresh, 'token_type': 'Bearer'}), 200

@auth_bp.route('/logout', methods=['POST'])
def logout():
    data = request.get_json() or {}
    if 'refresh_token' not in data:
        return jsonify({'message': 'Send refresh_token to revoke'}), 400
    try:
        payload = decode_token(data['refresh_token'])
    except Exception:
        return jsonify({'message': 'Invalid refresh token'}), 400
    if payload.get('type') != 'refresh':
        return jsonify({'message': 'Not a refresh token'}), 400

    rt = RefreshToken.query.filter_by(jti=payload['jti'], customer_id=int(payload['sub'])).first()
    if rt and not rt.revoked:
        rt.revoked = True
        db.session.commit()
    return jsonify({'message': 'Logged out (refresh revoked)'}), 200

@auth_bp.route('/me', methods=['GET'])
@auth_required()
def me():
    return jsonify(g.current_token), 200

@auth_bp.route('/google')
def login_google():
    if not hasattr(oauth, 'google'):
        return jsonify({'message': 'Google OAuth not configured'}), 501
    redirect_uri = url_for('auth.login_google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth_bp.route('/google/callback')
def login_google_callback():
    if not hasattr(oauth, 'google'):
        return jsonify({'message': 'Google OAuth not configured'}), 501
    token = oauth.google.authorize_access_token()
    userinfo = token.get('userinfo') or oauth.google.parse_id_token(token)
    email = userinfo.get('email')
    name = userinfo.get('name') or email.split('@')[0]
    if not email:
        return jsonify({'message': 'Google did not return email'}), 400

    user = Customer.query.filter_by(email=email).first()
    if not user:
        user = Customer(name=name, email=email, password_hash=generate_password_hash(uuid4().hex))
        role_user = Role.query.filter_by(name='user').first() or Role(name='user')
        db.session.add(role_user)
        user.roles = [role_user]
        db.session.add(user)
        db.session.commit()

    access = create_access_token(user)
    refresh = create_refresh_token(user)
    return jsonify({'token_type': 'Bearer', 'access_token': access, 'refresh_token': refresh}), 200
