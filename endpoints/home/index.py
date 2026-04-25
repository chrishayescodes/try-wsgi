import datetime
try:
    from middleware import allowverbs, inject_template, html_response
except ImportError:
    from infra.middleware import allowverbs, inject_template, html_response

# --- Pure Logic (Testable) ---
def get_home_data(now=None):
    if now is None:
        now = datetime.datetime.now()
    
    return {
        "user_name": "AdminUser",
        "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "is_morning": now.hour < 12
    }

# --- WSGI Handler (The Pipeline) ---
@allowverbs('GET')
@inject_template
@html_response
def application(environ, start_response, renderer=None, **kwargs):
    # 1. Prepare Data using pure logic
    data = get_home_data()

    # 2. Render using injected dependency
    return renderer.render('index.html', data)
