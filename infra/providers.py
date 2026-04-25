from jinja2 import Environment, FileSystemLoader
import os

class TemplateProvider:
    def __init__(self, template_dir='/var/www/silos'):
        self.loader = FileSystemLoader(template_dir)
        self.env = Environment(loader=self.loader)

    def render(self, template_name, data=None):
        if data is None:
            data = {}
        template = self.env.get_template(template_name)
        return template.render(data).encode('utf-8')

import jwt
import datetime

class AuthProvider:
    def authenticate(self, username, password):
        """Returns user_claims if successful, None otherwise."""
        raise NotImplementedError()

    def generate_tokens(self, claims, private_key_path=None):
        if private_key_path is None:
            private_key_path = os.environ.get('JWT_PRIVATE_KEY_PATH', '/etc/jwt-keys/jwt-private.pem')
        
        with open(private_key_path, 'r') as f:
            private_key = f.read()

        now = datetime.datetime.utcnow()

        # Expiry times from environment or defaults
        access_expiry = int(os.environ.get('JWT_ACCESS_EXP_SECONDS', 15 * 60))
        refresh_expiry = int(os.environ.get('JWT_REFRESH_EXP_SECONDS', 7 * 24 * 60 * 60))

        # Access Token
        access_payload = claims.copy()
        access_payload.update({
            "typ": "access",
            "iat": now,
            "exp": now + datetime.timedelta(seconds=access_expiry)
        })
        access_token = jwt.encode(access_payload, private_key, algorithm="RS256")

        # Refresh Token
        refresh_payload = claims.copy()
        refresh_payload.update({
            "typ": "refresh",
            "iat": now,
            "exp": now + datetime.timedelta(seconds=refresh_expiry)
        })

        refresh_token = jwt.encode(refresh_payload, private_key, algorithm="RS256")

        return access_token, refresh_token

class MockAuthProvider(AuthProvider):
    def authenticate(self, username, password):
        if username == "admin" and password == "password123":
            return {
                "sub": "1234567890",
                "name": "Admin User"
            }
        return None

class Container:
    def __init__(self):
        self._services = {}

    def register(self, name, service):
        self._services[name] = service

    def resolve(self, name):
        return self._services.get(name)

# Production Setup
container = Container()
container.register('renderer', TemplateProvider())
container.register('auth', MockAuthProvider())

def get_container():
    return container
