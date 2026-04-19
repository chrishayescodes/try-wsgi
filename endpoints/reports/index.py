import os
from jinja2 import Environment, FileSystemLoader
from middleware import require_jwt, logger, allowverbs

# Initialize the warm Jinja2 environment
loader = FileSystemLoader('/var/www/silos')
env = Environment(loader=loader)

@allowverbs('GET')
@require_jwt
def application(environ, start_response):
    # 1. Access the "Claims" injected by our middleware
    user_claims = environ.get('user_claims', {})
    user_name = user_claims.get('name', 'Valued Employee')
    
    # 2. Business Logic (Mocking a database call for report data)
    report_data = {
        "user_name": user_name,
        "generated_at": os.popen('date').read(),
        "stats": [
            {"label": "Active Silos", "value": 12},
            {"label": "Auth Requests", "value": "1,240"},
            {"label": "System Health", "value": "Optimal"}
        ]
    }

    # 3. Render the View
    template = env.get_template('reports.html')
    output = template.render(report_data)

    start_response('200 OK', [('Content-type', 'text/html')])
    return [output.encode('utf-8')]