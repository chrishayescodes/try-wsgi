from jinja2 import Environment, FileSystemLoader
import os
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

import logging

logger = logging.getLogger("silo_logger")

def render_template(template_name, data=None):
    """Simple functional wrapper for Jinja2 rendering."""
    env = get_jinja_env()
    template = env.get_template(template_name)
    return template.render(data or {}).encode('utf-8')

def validate_token(token, required_type='access', public_key_path=None):
    from infra.auth import validate_token as _validate_token
    return _validate_token(token, required_type=required_type, public_key_path=public_key_path)

def generate_tokens(claims, private_key_path=None):
    from infra.auth import generate_tokens as _generate_tokens
    return _generate_tokens(claims, private_key_path=private_key_path)

def mock_authenticate(username, password):
    from infra.auth import mock_authenticate as _mock_authenticate
    return _mock_authenticate(username, password)

# --- Service Registry ---

SERVICES = {
    'renderer': SimpleNamespace(render=render_template),
    'auth': SimpleNamespace(
        authenticate=mock_authenticate, 
        generate_tokens=generate_tokens,
        validate_token=validate_token
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
