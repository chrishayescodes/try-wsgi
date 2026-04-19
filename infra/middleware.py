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
            public_key_path = os.environ.get('JWT_PUBLIC_KEY_PATH', '/var/www/silos/jwt-public.pem')
            
            # 2. Determine which cookie to look for
            cookie_name = 'silo_token' if required_type == 'access' else 'refresh_token'
            
            cookie_header = environ.get('HTTP_COOKIE', '')
            cookie = http.cookies.SimpleCookie(cookie_header)
            
            token = None
            if cookie_name in cookie:
                token = cookie[cookie_name].value

            if not token:
                start_response('401 Unauthorized', [('Content-Type', 'text/plain')])
                return [f"Security Error: No {required_type} session found".encode()]

            try:
                # FIX: Ensure public_key is defined WITHIN the try block before use
                with open(public_key_path, 'r') as f:
                    public_key = f.read()

                # 3. Verify the Token
                payload = jwt.decode(
                    token, 
                    public_key, 
                    algorithms=["RS256"],
                    options={"verify_signature": True, "verify_exp": True}
                )

                # 4. CRITICAL: Check the token type claim
                if payload.get('typ') != required_type:
                    start_response('403 Forbidden', [('Content-Type', 'text/plain')])
                    return [b"Security Error: Token type mismatch"]

                environ['user_claims'] = payload
                return func(environ, start_response)
            except FileNotFoundError:
                start_response('500 Server Error', [('Content-Type', 'text/plain')])
                return [b'Server Error: Token']
            except jwt.ExpiredSignatureError:
                start_response('401 Unauthorized', [('Content-Type', 'text/plain')])
                return [b"Security Error: Token expired"]
            except (jwt.InvalidTokenError, FileNotFoundError) as e:
                start_response('401 Unauthorized', [('Content-Type', 'text/plain')])
                return [f"Security Error: {str(e)}".encode()]

        return wrapper
    return decorator
    