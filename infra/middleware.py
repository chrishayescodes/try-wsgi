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

def require_jwt(func):
    @functools.wraps(func)
    def wrapper(environ, start_response):
        # Configuration
        public_key_path = os.environ.get('JWT_PUBLIC_KEY_PATH', '/var/www/silos/jwt-public.pem')
        
        # 1. Look for Cookies in the environment
        cookie_header = environ.get('HTTP_COOKIE', '')
        cookie = http.cookies.SimpleCookie(cookie_header)
        
        # 2. Extract our specific token
        token = None
        if 'silo_token' in cookie:
            token = cookie['silo_token'].value

        if not token:
            start_response('401 Unauthorized', [('Content-Type', 'text/plain')])
            return [b"Security Error: No session found"]

        try:
            # 3. Read the Public Key (Certificate)
            with open(public_key_path, 'r') as f:
                public_key = f.read()

            # 4. Verify the Token
            # PyJWT validates: Signature, Expiration (exp), and Not Before (nbf)
            payload = jwt.decode(
                token, 
                public_key, 
                algorithms=["RS256"],
                # Standard enterprise options:
                options={"verify_signature": True, "verify_exp": True}
            )

            # 5. Injection: Pass the Claims/Identity to the Silo
            # Equivalent to HttpContext.User.Claims in .NET
            environ['user_claims'] = payload
            
            # Continue to the Silo (the "Action Filter" passed)
            return func(environ, start_response)

        except jwt.ExpiredSignatureError:
            start_response('401 Unauthorized', [('Content-Type', 'text/plain')])
            return [b"Security Error: Token has expired"]
            
        except jwt.InvalidTokenError as e:
            start_response('401 Unauthorized', [('Content-Type', 'text/plain')])
            # Log the specific error to Apache error logs for debugging
            print(f"[AUTH ERROR] {str(e)}", file=environ['wsgi.errors'])
            return [b"Security Error: Invalid token signature"]
            
        except FileNotFoundError:
            start_response('500 Internal Server Error', [('Content-Type', 'text/plain')])
            return [b"Configuration Error: Public Key not found on server"]

    return wrapper