import jwt
import functools
import os
import http.cookies
import logging
import urllib.parse
import json

try:
    from providers import get_container
except ImportError:
    from infra.providers import get_container

# Set up a simple logger for the silos
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("silo_logger")

def allowverbs(*verbs):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(environ, start_response, **kwargs):
            if environ.get('REQUEST_METHOD') not in verbs:
                start_response('405 Method Not Allowed', [('Content-Type', 'text/plain')])
                return [b"Method Not Allowed"]
            return func(environ, start_response, **kwargs)
        return wrapper
    return decorator

def require_jwt(required_type='access'):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(environ, start_response, **kwargs):
            # 1. Configuration
            public_key_path = environ.get('JWT_PUBLIC_KEY_PATH') or \
                              os.environ.get('JWT_PUBLIC_KEY_PATH') or \
                              '/etc/jwt-keys/jwt-public.pem'
                              
            # 2. Determine which cookie to look for
            cookie_name = 'silo_token' if required_type == 'access' else 'refresh_token'
            
            cookie_header = environ.get('HTTP_COOKIE', '')
            cookie = http.cookies.SimpleCookie(cookie_header)
            
            token = None
            if cookie_name in cookie:
                token = cookie[cookie_name].value

            if not token:
                logger.error("Security Failure: No token found in cookies")
                
                # Redirect to login silo
                start_response('303 See Other', [
                    ('Location', '/login'),
                    ('Content-Type', 'text/plain')
                ])
                return [b"Security Error: Redirecting to login..."]

            try:
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
                    start_response('403 Forbidden', [('Content-Type', 'text/plain')])
                    return [b"Security Error: Token type mismatch"]

                environ['user_claims'] = payload
                kwargs['user_claims'] = payload
                return func(environ, start_response, **kwargs)
                
            except jwt.ExpiredSignatureError:
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

def inject_template(func):
    @functools.wraps(func)
    def wrapper(environ, start_response, **kwargs):
        container = get_container()
        kwargs['renderer'] = container.resolve('renderer')
        return func(environ, start_response, **kwargs)
    return wrapper

def inject_params(func):
    @functools.wraps(func)
    def wrapper(environ, start_response, **kwargs):
        query_string = environ.get('QUERY_STRING', '')
        params = urllib.parse.parse_qs(query_string)
        flat_params = {k: v[0] if v else None for k, v in params.items()}
        kwargs['params'] = flat_params
        return func(environ, start_response, **kwargs)
    return wrapper

def inject_auth(func):
    @functools.wraps(func)
    def wrapper(environ, start_response, **kwargs):
        container = get_container()
        kwargs['auth'] = container.resolve('auth')
        return func(environ, start_response, **kwargs)
    return wrapper

def json_response(func):
    @functools.wraps(func)
    def wrapper(environ, start_response, **kwargs):
        result = func(environ, start_response, **kwargs)
        if isinstance(result, list):
            return result
            
        start_response('200 OK', [('Content-Type', 'application/json')])
        if isinstance(result, (dict, list)):
            return [json.dumps(result).encode('utf-8')]
        return [result]
    return wrapper

def html_response(func):
    @functools.wraps(func)
    def wrapper(environ, start_response, **kwargs):
        result = func(environ, start_response, **kwargs)
        if isinstance(result, list):
            return result
            
        start_response('200 OK', [('Content-Type', 'text/html')])
        if isinstance(result, str):
            return [result.encode('utf-8')]
        return [result]
    return wrapper
