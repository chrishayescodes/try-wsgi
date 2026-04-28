from infra.middleware import allowverbs, html_response
from infra.auth import delete_auth_cookies

@allowverbs('POST')
@html_response
def application(environ, start_response, **kwargs):
    headers = [('Location', '/')]
    headers.extend(delete_auth_cookies())

    return b"Redirecting...", '302 Found', headers
