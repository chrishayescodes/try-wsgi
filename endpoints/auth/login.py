import jwt
import datetime
import json
import os
import http.cookies # Cleaner cookie management
from jinja2 import Environment, FileSystemLoader
from middleware import allowverbs

PRIVATE_KEY_PATH = "/etc/jwt-keys/jwt-private.pem"

template_env = Environment(loader=FileSystemLoader('/var/www/silos'))

@allowverbs('POST','GET')
def application(environ,start_response):
    method = environ.get('REQUEST_METHOD', 'GET')

    if method == 'GET':
        return handle_get(environ, start_response)
    
    return handle_post(environ, start_response)

def handle_get(environ, start_response):
    template = template_env.get_template('login.html')
    # If you want to pass a message (like 'session expired'), you can pull from query params
    output = template.render()
    start_response('200 OK', [('Content-Type', 'text/html')])
    return [output.encode('utf-8')]

def handle_post(environ, start_response):
    try:
        request_body_size = int(environ.get('CONTENT_LENGTH', 0))
        request_body = environ['wsgi.input'].read(request_body_size)
        data = json.loads(request_body)
        
        username = data.get('username')
        password = data.get('password')

        if username == "admin" and password == "password123":
            with open(PRIVATE_KEY_PATH, 'r') as f:
                private_key = f.read()

            now = datetime.datetime.utcnow()

            # 1. GENERATE ACCESS TOKEN (Short-lived)
            # This fixes your 403 error by adding the 'typ' claim
            access_payload = {
                "sub": "1234567890",
                "name": "Admin User",
                "typ": "access", # CRITICAL: Middleware looks for this
                "iat": now,
                "exp": now + datetime.timedelta(minutes=15)
            }
            access_token = jwt.encode(access_payload, private_key, algorithm="RS256")

            # 2. GENERATE REFRESH TOKEN (Long-lived)
            refresh_payload = {
                "sub": "1234567890",
                "name": "Admin User",
                "typ": "refresh", # CRITICAL: /refresh endpoint looks for this
                "iat": now,
                "exp": now + datetime.timedelta(days=7)
            }
            refresh_token = jwt.encode(refresh_payload, private_key, algorithm="RS256")

            # 3. CONSTRUCT COOKIES
            # Using http.cookies.SimpleCookie is much safer than f-strings
            cookie = http.cookies.SimpleCookie()
            
            # Access Cookie
            cookie['silo_token'] = access_token
            cookie['silo_token']['httponly'] = True
            cookie['silo_token']['path'] = '/'
            cookie['silo_token']['samesite'] = 'Lax' # Better for redirects

            # Refresh Cookie
            cookie['refresh_token'] = refresh_token
            cookie['refresh_token']['httponly'] = True
            cookie['refresh_token']['path'] = '/refresh' # Scoped only to refresh endpoint
            cookie['refresh_token']['samesite'] = 'Lax'

            headers = [
                ('Content-Type', 'application/json'),
                ('Set-Cookie', cookie['silo_token'].OutputString()),
                ('Set-Cookie', cookie['refresh_token'].OutputString())
            ]
            
            start_response('200 OK', headers)
            return [json.dumps({"status": "success"}).encode('utf-8')]

        else:
            start_response('401 Unauthorized', [('Content-Type', 'application/json')])
            return [json.dumps({"status": "error", "error": "Invalid credentials"}).encode('utf-8')]

    except Exception as e:
        print(f"CRITICAL LOGIN ERROR: {str(e)}", file=environ['wsgi.errors'])
        start_response('500 Internal Server Error', [('Content-Type', 'text/plain')])
        return [f"Server Error: {str(e)}".encode('utf-8')]