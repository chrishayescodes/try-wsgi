import datetime
import functools
import http.cookies
import jwt
import logging
import os
from infra.providers import get_container

logger = logging.getLogger("silo_logger")


def validate_token(token, required_type='access', public_key_path=None):
    """Decodes and validates a JWT token."""
    if not public_key_path:
        public_key_path = os.environ.get('JWT_PUBLIC_KEY_PATH', '/etc/jwt-keys/jwt-public.pem')

    if not os.path.exists(public_key_path):
        logger.error(f"Public key not found at {public_key_path}")
        raise FileNotFoundError(f"Public key not found at {public_key_path}")

    with open(public_key_path, 'r') as f:
        public_key = f.read()

    payload = jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        options={"verify_signature": True, "verify_exp": True}
    )

    if payload.get('typ') != required_type:
        raise jwt.InvalidTokenError("Token type mismatch")

    return payload


def generate_tokens(claims, private_key_path=None):
    """Pure function to generate JWT tokens."""
    if private_key_path is None:
        private_key_path = os.environ.get('JWT_PRIVATE_KEY_PATH', '/etc/jwt-keys/jwt-private.pem')

    with open(private_key_path, 'r') as f:
        private_key = f.read()

    now = datetime.datetime.utcnow()
    access_expiry = int(os.environ.get('JWT_ACCESS_EXP_SECONDS', 15 * 60))
    refresh_expiry = int(os.environ.get('JWT_REFRESH_EXP_SECONDS', 7 * 24 * 60 * 60))

    access_payload = {**claims, "typ": "access", "iat": now, "exp": now + datetime.timedelta(seconds=access_expiry)}
    access_token = jwt.encode(access_payload, private_key, algorithm="RS256")

    refresh_payload = {**claims, "typ": "refresh", "iat": now, "exp": now + datetime.timedelta(seconds=refresh_expiry)}
    refresh_token = jwt.encode(refresh_payload, private_key, algorithm="RS256")

    return access_token, refresh_token


def mock_authenticate(username, password):
    """Mock authentication logic."""
    if username == "admin" and password == "password123":
        return {"sub": "1234567890", "name": "Admin User"}
    return None


def require_jwt(required_type='access'):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(environ, start_response, **kwargs):
            auth = get_container().resolve('auth')
            cookie_name = 'silo_token' if required_type == 'access' else 'refresh_token'

            cookie_header = environ.get('HTTP_COOKIE', '')
            cookie = http.cookies.SimpleCookie(cookie_header)

            token = None
            if cookie_name in cookie:
                token = cookie[cookie_name].value

            if not token:
                logger.error(f"Security Failure: No {required_type} token found in cookies")
                start_response('303 See Other', [
                    ('Location', '/login'),
                    ('Content-Type', 'text/plain')
                ])
                return [b"Security Error: Redirecting to login..."]

            try:
                payload = auth.validate_token(token, required_type=required_type)
                environ['user_claims'] = payload
                kwargs['user_claims'] = payload
                return func(environ, start_response, **kwargs)

            except jwt.ExpiredSignatureError:
                if required_type == 'refresh':
                    start_response('303 See Other', [('Location', '/login')])
                    return [b"Session expired"]

                script_name = environ.get('SCRIPT_NAME', '')
                path_info = environ.get('PATH_INFO', '')
                query_string = environ.get('QUERY_STRING', '')

                current_url = f"{script_name}{path_info}"
                if query_string:
                    current_url += f"?{query_string}"

                start_response('303 See Other', [
                    ('Location', f'/refresh?next={current_url}'),
                    ('Content-Type', 'text/plain')
                ])
                return [b"Redirecting to session refresh..."]

            except (jwt.InvalidTokenError, FileNotFoundError) as e:
                logger.error(f"Security Failure: {str(e)}")
                start_response('303 See Other', [
                    ('Location', '/login'),
                    ('Content-Type', 'text/plain')
                ])
                return [b"Security Error: Redirecting to login..."]

        return wrapper
    return decorator


def inject_auth(func):
    @functools.wraps(func)
    def wrapper(environ, start_response, **kwargs):
        container = get_container()
        kwargs['auth'] = container.resolve('auth')
        return func(environ, start_response, **kwargs)
    return wrapper


def get_auth_cookies(access_token, refresh_token):
    """Returns a list of ('Set-Cookie', value) tuples for access and refresh tokens."""
    cookie = http.cookies.SimpleCookie()
    cookie['silo_token'] = access_token
    cookie['silo_token']['httponly'] = True
    cookie['silo_token']['path'] = '/'
    cookie['silo_token']['samesite'] = 'Lax'

    cookie['refresh_token'] = refresh_token
    cookie['refresh_token']['httponly'] = True
    cookie['refresh_token']['path'] = '/refresh'
    cookie['refresh_token']['samesite'] = 'Lax'

    return [
        ('Set-Cookie', cookie['silo_token'].OutputString()),
        ('Set-Cookie', cookie['refresh_token'].OutputString())
    ]


def delete_auth_cookies():
    """Returns a list of ('Set-Cookie', value) tuples that expire the auth cookies."""
    cookie = http.cookies.SimpleCookie()

    cookie['silo_token'] = ''
    cookie['silo_token']['path'] = '/'
    cookie['silo_token']['expires'] = 'Thu, 01 Jan 1970 00:00:00 GMT'

    cookie['refresh_token'] = ''
    cookie['refresh_token']['path'] = '/refresh'
    cookie['refresh_token']['expires'] = 'Thu, 01 Jan 1970 00:00:00 GMT'

    return [
        ('Set-Cookie', cookie['silo_token'].OutputString()),
        ('Set-Cookie', cookie['refresh_token'].OutputString())
    ]
