from infra.middleware import allowverbs, delete_auth_cookies

@allowverbs('POST')
def application(environ, start_response, **kwargs):
    headers = [('Location', '/')]
    headers.extend(delete_auth_cookies())

    start_response('302 Found', headers)
    return [b"Redirecting..."]
