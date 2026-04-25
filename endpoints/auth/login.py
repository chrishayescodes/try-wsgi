import json
import http.cookies
try:
    from middleware import allowverbs, inject_template, inject_auth, html_response, json_response
except ImportError:
    from infra.middleware import allowverbs, inject_template, inject_auth, html_response, json_response

@allowverbs('GET', 'POST')
@inject_template
@inject_auth
def application(environ, start_response, renderer=None, auth=None, **kwargs):
    method = environ.get('REQUEST_METHOD', 'GET')
    
    if method == 'GET':
        return handle_get(renderer)
    
    return handle_post(environ, start_response, auth)

def handle_get(renderer):
    return [renderer.render('login.html')]

def handle_post(environ, start_response, auth):
    try:
        request_body_size = int(environ.get('CONTENT_LENGTH', 0))
        request_body = environ['wsgi.input'].read(request_body_size)
        data = json.loads(request_body)
        
        username = data.get('username')
        password = data.get('password')

        claims = auth.authenticate(username, password)
        if claims:
            access_token, refresh_token = auth.generate_tokens(claims)

            cookie = http.cookies.SimpleCookie()
            cookie['silo_token'] = access_token
            cookie['silo_token']['httponly'] = True
            cookie['silo_token']['path'] = '/'
            cookie['silo_token']['samesite'] = 'Lax'

            cookie['refresh_token'] = refresh_token
            cookie['refresh_token']['httponly'] = True
            cookie['refresh_token']['path'] = '/refresh'
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
        start_response('500 Internal Server Error', [('Content-Type', 'text/plain')])
        return [f"Server Error: {str(e)}".encode('utf-8')]
