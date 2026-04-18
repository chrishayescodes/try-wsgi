from jinja2 import Environment, FileSystemLoader
import os
import datetime

# Initialize Jinja environment (remains warm in RAM)
loader = FileSystemLoader(os.path.dirname(__file__))
env = Environment(loader=loader)

def application(environ, start_response):
    status = '200 OK'
    headers = [('Content-type', 'text/html')]
    start_response(status, headers)

    # 1. Prepare Data
    now = datetime.datetime.now()
    
    data = {
        "user_name": "AdminUser",
        "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "is_morning": now.hour < 12
    }

    # 2. Render
    template = env.get_template('hello.html')
    output = template.render(data)

    return [output.encode('utf-8')]