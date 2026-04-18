import datetime

def application(environ, start_response):
    status = '200 OK'
    headers = [('Content-type', 'text/html')]
    start_response(status, headers)

    now = datetime.datetime.now()
    
    # Simple, straightforward HTML output
    content = f"""
    <html>
        <body>
            <h1>Siloed Performance</h1>
            <p>Route: /api/hello</p>
            <p>Server Time: {now.strftime('%Y-%m-%d %H:%M:%S')}</p>
        </body>
    </html>
    """
    return [content.encode('utf-8')]