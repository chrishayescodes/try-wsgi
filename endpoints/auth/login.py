import json
from infra.middleware import allowverbs, inject_template, html_response, json_response, json_body
from infra.auth import inject_auth, get_auth_cookies

@allowverbs('GET', 'POST')
@inject_template
@inject_auth
@html_response
def application(environ, start_response, renderer=None, auth=None, **kwargs):
    method = environ.get('REQUEST_METHOD', 'GET')
    
    if method == 'GET':
        return handle_get(renderer)
    
    return handle_post(environ, start_response, auth=auth, **kwargs)

def handle_get(renderer):
    return renderer.render('login.html')

@json_body
@json_response
def handle_post(environ, start_response, auth=None, body=None, **kwargs):
    username = body.get('username')
    password = body.get('password')

    claims = auth.authenticate(username, password)
    if claims:
        access_token, refresh_token = auth.generate_tokens(claims)
        headers = get_auth_cookies(access_token, refresh_token)
        return {"status": "success"}, '200 OK', headers

    return {"status": "error", "error": "Invalid credentials"}, '401 Unauthorized', []
