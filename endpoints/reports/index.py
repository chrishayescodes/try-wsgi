import os
try:
    from middleware import require_jwt, allowverbs, inject_template, html_response
except ImportError:
    from infra.middleware import require_jwt, allowverbs, inject_template, html_response

@allowverbs('GET')
@require_jwt(required_type='access')
@inject_template
@html_response
def application(environ, start_response, renderer=None, user_claims=None, **kwargs):
    # 1. Access the "Claims" injected by our middleware
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

    # 3. Render using injected dependency
    return renderer.render('reports.html', report_data)
