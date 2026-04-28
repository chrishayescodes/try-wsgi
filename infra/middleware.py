import jwt
import functools
import os
import http.cookies
import logging
import urllib.parse
import json
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
            auth = get_container().resolve('auth')
            
            # Determine which cookie to look for
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

def json_body(func):
    """Parses JSON from the request body and injects it into kwargs."""
    @functools.wraps(func)
    def wrapper(environ, start_response, **kwargs):
        try:
            content_length = int(environ.get('CONTENT_LENGTH', 0))
            if content_length > 0:
                body = environ['wsgi.input'].read(content_length)
                kwargs['body'] = json.loads(body)
            else:
                kwargs['body'] = {}
        except (ValueError, json.JSONDecodeError):
            start_response('400 Bad Request', [('Content-Type', 'text/plain')])
            return [b"Invalid JSON body"]
        
        return func(environ, start_response, **kwargs)
    return wrapper

def _process_response(result, default_content_type):
    """Helper to normalize handler return values."""
    status = '200 OK'
    headers = [('Content-Type', default_content_type)]
    body = result

    if isinstance(result, tuple):
        if len(result) >= 1:
            body = result[0]
        if len(result) >= 2:
            status = result[1]
        if len(result) >= 3:
            headers.extend(result[2])
    
    return body, status, headers

def json_response(func):
    @functools.wraps(func)
    def wrapper(environ, start_response, **kwargs):
        result = func(environ, start_response, **kwargs)
        if isinstance(result, list): # Already a WSGI response
            return result
            
        body, status, headers = _process_response(result, 'application/json')
        
        start_response(status, headers)
        if isinstance(body, (dict, list)):
            return [json.dumps(body).encode('utf-8')]
        if isinstance(body, str):
            return [body.encode('utf-8')]
        return [body]
    return wrapper

def html_response(func):
    @functools.wraps(func)
    def wrapper(environ, start_response, **kwargs):
        result = func(environ, start_response, **kwargs)
        if isinstance(result, list): # Already a WSGI response
            return result
            
        body, status, headers = _process_response(result, 'text/html')

        start_response(status, headers)
        if isinstance(body, str):
            return [body.encode('utf-8')]
        return [body]
    return wrapper

def get_auth_cookies(access_token, refresh_token):
    """
    Returns a list of ('Set-Cookie', value) tuples for access and refresh tokens.
    """
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
    """
    Returns a list of ('Set-Cookie', value) tuples that expire the auth cookies.
    """
    cookie = http.cookies.SimpleCookie()
    
    # Expire the Access Token
    cookie['silo_token'] = ''
    cookie['silo_token']['path'] = '/'
    cookie['silo_token']['expires'] = 'Thu, 01 Jan 1970 00:00:00 GMT'

    # Expire the Refresh Token
    cookie['refresh_token'] = ''
    cookie['refresh_token']['path'] = '/refresh'
    cookie['refresh_token']['expires'] = 'Thu, 01 Jan 1970 00:00:00 GMT'

    return [
        ('Set-Cookie', cookie['silo_token'].OutputString()),
        ('Set-Cookie', cookie['refresh_token'].OutputString())
    ]
