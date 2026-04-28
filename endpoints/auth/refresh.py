import json
from urllib.parse import parse_qs
from infra.middleware import allowverbs, require_jwt, inject_template, inject_auth, json_response, html_response, get_auth_cookies

@allowverbs('POST', 'GET')
@inject_template
@inject_auth
@html_response
def application(environ, start_response, renderer=None, auth=None, **kwargs):
    method = environ.get('REQUEST_METHOD', 'GET')

    if method == 'GET':
        return handle_get(environ, start_response, renderer=renderer, **kwargs)
    
    return handle_post(environ, start_response, auth=auth, **kwargs)

@require_jwt(required_type='refresh')
@json_response
def handle_post(environ, start_response, auth=None, user_claims=None, **kwargs):
    claims = user_claims or {}
    
    # Use the AuthProvider to generate NEW tokens (Rotation)
    # We pass the existing claims (sub, name) to keep the identity
    clean_claims = {
        "sub": claims.get('sub'),
        "name": claims.get('name')
    }
    access_token, refresh_token = auth.generate_tokens(clean_claims)

    headers = get_auth_cookies(access_token, refresh_token)
    return {"status": "refreshed"}, '200 OK', headers

def handle_get(environ, start_response, renderer, **kwargs):
    query = parse_qs(environ.get('QUERY_STRING', ''))
    next_url = query.get('next', ['/'])[0]
    
    return renderer.render('refresh.html', {"next_url": next_url})
