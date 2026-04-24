import jwt
import datetime
import http.cookies
from middleware import allowverbs, require_jwt
from jinja2 import Environment, FileSystemLoader
from urllib.parse import parse_qs

# Key paths (linked into /var/www/silos/ by postcreate.sh)
PUBLIC_KEY_PATH = '/etc/jwt-keys/jwt-public.pem'
PRIVATE_KEY_PATH = '/etc/jwt-keys/jwt-private.pem'

@allowverbs('POST', 'GET')
def application(environ, start_response):
    method = environ.get('REQUEST_METHOD', 'GET')

    if method == 'GET':
        return handle_get(environ, start_response)
    
    return handle_post(environ, start_response)

@require_jwt(required_type='refresh')
def handle_post(environ, start_response):
    # Claims extracted from the Refresh Token by middleware
    claims = environ.get('user_claims', {})
    
    try:
        with open(PRIVATE_KEY_PATH, 'r') as f:
            private_key = f.read()

        # Generate NEW Access Token
        now = datetime.datetime.utcnow()
        payload = {
            "sub": claims.get('sub'),
            "name": claims.get('name'),
            "typ": "access", # This is the critical distinction
            "iat": now,
            "exp": now + datetime.timedelta(seconds=15)
        }
        
        new_access_token = jwt.encode(payload, private_key, algorithm="RS256")

        # Set the Access Token Cookie
        cookie = http.cookies.SimpleCookie()
        cookie['silo_token'] = new_access_token
        cookie['silo_token']['httponly'] = True
        cookie['silo_token']['path'] = '/'
        cookie['silo_token']['samesite'] = 'Lax'

        start_response('200 OK', [
            ('Content-Type', 'application/json'),
            ('Set-Cookie', cookie['silo_token'].OutputString())
        ])
        return [b'{"status": "refreshed"}']

    except Exception as e:
        start_response('500 Internal Server Error', [('Content-Type', 'text/plain')])
        return [f"Refresh failed: {str(e)}".encode()]

template_env = Environment(loader=FileSystemLoader('/var/www/silos'))

def handle_get(environ, start_response):
    # Get the redirect target
    query = parse_qs(environ.get('QUERY_STRING', ''))
    next_url = query.get('next', ['/'])[0]
    
    # Load and render the template
    template = template_env.get_template('refresh.html')
    output = template.render(next_url=next_url)

    start_response('200 OK', [('Content-Type', 'text/html')])
    return [output.encode('utf-8')]