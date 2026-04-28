from jinja2 import Environment, FileSystemLoader
import os
import jwt
import datetime
from types import SimpleNamespace

# --- Base Interfaces (kept for testing/mocking) ---

class TemplateProvider:
    def render(self, template_name, data=None):
        raise NotImplementedError()

class AuthProvider:
    def authenticate(self, username, password):
        raise NotImplementedError()
    def generate_tokens(self, claims, private_key_path=None):
        raise NotImplementedError()

# --- Functional Implementation ---

_jinja_env = None

def get_jinja_env():
    global _jinja_env
    if _jinja_env is None:
        template_dir = os.environ.get('TEMPLATE_DIR', '/var/www/silos')
        # Handle cases where the directory might not exist during testing
        if not os.path.exists(template_dir):
            template_dir = os.path.join(os.getcwd(), 'templates')
        _jinja_env = Environment(loader=FileSystemLoader(template_dir))
    return _jinja_env

def render_template(template_name, data=None):
    """Simple functional wrapper for Jinja2 rendering."""
    env = get_jinja_env()
    template = env.get_template(template_name)
    return template.render(data or {}).encode('utf-8')

def generate_tokens(claims, private_key_path=None):
    """Pure function to generate JWT tokens."""
    if private_key_path is None:
        private_key_path = os.environ.get('JWT_PRIVATE_KEY_PATH', '/etc/jwt-keys/jwt-private.pem')
    
    with open(private_key_path, 'r') as f:
        private_key = f.read()

    now = datetime.datetime.utcnow()
    access_expiry = int(os.environ.get('JWT_ACCESS_EXP_SECONDS', 15 * 60))
    refresh_expiry = int(os.environ.get('JWT_REFRESH_EXP_SECONDS', 7 * 24 * 60 * 60))

    # Access Token
    access_payload = {**claims, "typ": "access", "iat": now, "exp": now + datetime.timedelta(seconds=access_expiry)}
    access_token = jwt.encode(access_payload, private_key, algorithm="RS256")

    # Refresh Token
    refresh_payload = {**claims, "typ": "refresh", "iat": now, "exp": now + datetime.timedelta(seconds=refresh_expiry)}
    refresh_token = jwt.encode(refresh_payload, private_key, algorithm="RS256")

    return access_token, refresh_token

def mock_authenticate(username, password):
    """Mock authentication logic."""
    if username == "admin" and password == "password123":
        return {"sub": "1234567890", "name": "Admin User"}
    return None

# --- Service Registry ---

SERVICES = {
    'renderer': SimpleNamespace(render=render_template),
    'auth': SimpleNamespace(
        authenticate=mock_authenticate, 
        generate_tokens=generate_tokens
    )
}

class Container:
    """Minimal shim to keep existing DI calls working."""
    @staticmethod
    def register(name, service):
        SERVICES[name] = service

    @staticmethod
    def resolve(name):
        return SERVICES.get(name)

def get_container():
    return Container
