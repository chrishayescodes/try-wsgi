import json
import http.cookies
from urllib.parse import parse_qs
from infra.middleware import allowverbs, inject_template, html_response, json_response
from infra.auth import require_jwt, inject_auth, get_auth_cookies

@allowverbs('POST', 'GET')
@inject_template
@inject_auth
@html_response
def application(environ, start_response, renderer=None, auth=None, **kwargs):
    method = environ.get('REQUEST_METHOD', 'GET')

    if method == 'GET':
        return handle_get(environ, start_response, renderer=renderer, auth=auth, **kwargs)
    
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

def handle_get(environ, start_response, renderer, auth=None, **kwargs):
    query = parse_qs(environ.get('QUERY_STRING', ''))
    next_url = query.get('next', ['/'])[0]
    
    # Attempt "Silent" Server-Side Refresh
    # If we have a valid refresh token, we can just 303 redirect immediately
    # with the new cookies. This avoids the loading page appearing in history.
    cookie_header = environ.get('HTTP_COOKIE', '')
    cookie = http.cookies.SimpleCookie(cookie_header)
    
    if 'refresh_token' in cookie and auth:
        try:
            token = cookie['refresh_token'].value
            claims = auth.validate_token(token, required_type='refresh')
            
            # Generate new tokens (Rotation)
            clean_claims = {"sub": claims.get('sub'), "name": claims.get('name')}
            access_token, refresh_token = auth.generate_tokens(clean_claims)
            
            headers = get_auth_cookies(access_token, refresh_token)
            headers.append(('Location', next_url))
            
            start_response('303 See Other', headers)
            return [b"Redirecting..."]
        except Exception:
            # Token might be expired or invalid, fall back to the UI
            # so we can show a proper "Session Expired" message.
            pass

    return renderer.render('refresh.html', {"next_url": next_url})
