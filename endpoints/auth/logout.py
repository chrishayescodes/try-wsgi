from infra.middleware import allowverbs, delete_auth_cookies, html_response

@allowverbs('POST')
@html_response
def application(environ, start_response, **kwargs):
    headers = [('Location', '/')]
    headers.extend(delete_auth_cookies())

    return b"Redirecting...", '302 Found', headers
