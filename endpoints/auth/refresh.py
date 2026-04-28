import json
from urllib.parse import parse_qs

try:
    from middleware import allowverbs, require_jwt, inject_template, inject_auth, json_response, get_auth_cookies
except ImportError:
    from infra.middleware import allowverbs, require_jwt, inject_template, inject_auth, json_response, get_auth_cookies

@allowverbs('POST', 'GET')
@inject_template
@inject_auth
def application(environ, start_response, renderer=None, auth=None, **kwargs):
    method = environ.get('REQUEST_METHOD', 'GET')

    if method == 'GET':
        return handle_get(environ, start_response, renderer=renderer, **kwargs)
    
    return handle_post(environ, start_response, auth=auth, **kwargs)

@require_jwt(required_type='refresh')
def handle_post(environ, start_response, auth=None, user_claims=None, **kwargs):
    claims = user_claims or {}
    
    try:
        # Use the AuthProvider to generate NEW tokens (Rotation)
        # We pass the existing claims (sub, name) to keep the identity
        clean_claims = {
            "sub": claims.get('sub'),
            "name": claims.get('name')
        }
        access_token, refresh_token = auth.generate_tokens(clean_claims)

        headers = [('Content-Type', 'application/json')]
        headers.extend(get_auth_cookies(access_token, refresh_token))

        start_response('200 OK', headers)
        return [json.dumps({"status": "refreshed"}).encode('utf-8')]

    except Exception as e:
        start_response('500 Internal Server Error', [('Content-Type', 'text/plain')])
        return [f"Refresh failed: {str(e)}".encode()]

def handle_get(environ, start_response, renderer, **kwargs):
    query = parse_qs(environ.get('QUERY_STRING', ''))
    next_url = query.get('next', ['/'])[0]
    
    output = renderer.render('refresh.html', {"next_url": next_url})

    start_response('200 OK', [('Content-Type', 'text/html')])
    return [output]
