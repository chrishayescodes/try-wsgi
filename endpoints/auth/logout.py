import http.cookies
from middleware import allowverbs

@allowverbs('POST')
def application(environ, start_response):
    cookie = http.cookies.SimpleCookie()
    
    # Expire the Access Token
    cookie['silo_token'] = ''
    cookie['silo_token']['path'] = '/'
    cookie['silo_token']['expires'] = 'Thu, 01 Jan 1970 00:00:00 GMT'

    # Expire the Refresh Token (Must match the original path!)
    cookie['refresh_token'] = ''
    cookie['refresh_token']['path'] = '/refresh'
    cookie['refresh_token']['expires'] = 'Thu, 01 Jan 1970 00:00:00 GMT'

    start_response('302 Found', [
        ('Set-Cookie', cookie['silo_token'].OutputString()),
        ('Set-Cookie', cookie['refresh_token'].OutputString()),
        ('Location', '/')
    ])
    return [b"Redirecting..."]