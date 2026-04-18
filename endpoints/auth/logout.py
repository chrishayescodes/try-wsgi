import json
from middleware import allowverbs

@allowverbs('POST')
def application(environ, start_response):
    # To clear an HttpOnly cookie, we send it back with an expired date
    cookie_value = "silo_token=; Path=/; HttpOnly; SameSite=Strict; Expires=Thu, 01 Jan 1970 00:00:00 GMT"
    
    headers = [
        ('Content-Type', 'application/json'),
        ('Set-Cookie', cookie_value)
    ]
    
    start_response('200 OK', headers)
    return [json.dumps({"status": "success", "message": "Logged out"}).encode('utf-8')]
