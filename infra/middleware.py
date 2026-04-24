import jwt
import functools
import os
import http.cookies
import logging

# Set up a simple logger for the silos
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("silo_logger")

# The decorator is initialized once, but we pull the key inside the wrapper
# to handle any environment variable injections from Apache.

def allowverbs(*verbs):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(environ, start_response):
            if environ.get('REQUEST_METHOD') not in verbs:
                start_response('405 Method Not Allowed', [('Content-Type', 'text/plain')])
                return [b"Method Not Allowed"]
            return func(environ, start_response)
        return wrapper
    return decorator

def require_jwt(required_type='access'):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(environ, start_response):
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
                return func(environ, start_response)
                
            except jwt.ExpiredSignatureError:
                # Get the current URL to pass as the 'next' parameter
                script_name = environ.get('SCRIPT_NAME', '')
                path_info = environ.get('PATH_INFO', '')
                query_string = environ.get('QUERY_STRING', '')
                
                current_url = f"{script_name}{path_info}"
                if query_string:
                    current_url += f"?{query_string}"

                # Redirect to the refresh page (303 See Other)
                # This triggers your new refresh.py GET logic
                start_response('303 See Other', [
                    ('Location', f'/refresh?next={current_url}'),
                    ('Content-Type', 'text/plain')
                ])
                return [b"Redirecting to session refresh..."]

            # middleware.py

            except (jwt.InvalidTokenError, FileNotFoundError) as e:
                logger.error(f"Security Failure: {str(e)}")
                
                # Redirect to login silo
                start_response('303 See Other', [
                    ('Location', '/login'),
                    ('Content-Type', 'text/plain')
                ])
                return [b"Security Error: Redirecting to login..."]

        return wrapper
    return decorator
    