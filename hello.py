from jinja2 import Environment, FileSystemLoader
import os

# Initialize the environment pointing to our silo directory
# This happens once when the daemon starts/reloads
loader = FileSystemLoader(os.path.dirname(__file__))
env = Environment(loader=loader)

def application(environ, start_response):
    status = '200 OK'
    headers = [('Content-type', 'text/html')]
    start_response(status, headers)

    # 1. Logic
    data = {
        "user_name": "AdminUser",
    }

    # 2. Render (Jinja handles the "merging" of base and hello)
    template = env.get_template('hello.html')
    output = template.render(data)

    return [output.encode('utf-8')]