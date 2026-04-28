import unittest
from unittest.mock import MagicMock
import json
import io
import os
import jwt
import datetime
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

from endpoints.auth.login import application as login_app
from endpoints.auth.refresh import application as refresh_app
from endpoints.reports.index import application as reports_app
from infra.providers import get_container, AuthProvider

class TestIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Generate RSA keys for testing
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        cls.private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        cls.public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        # Mock keys in filesystem if necessary, or just override environment
        cls.pub_key_path = 'tests/test_pub.pem'
        cls.priv_key_path = 'tests/test_priv.pem'
        with open(cls.pub_key_path, 'wb') as f:
            f.write(cls.public_pem)
        with open(cls.priv_key_path, 'wb') as f:
            f.write(cls.private_pem)
        
        os.environ['JWT_PUBLIC_KEY_PATH'] = cls.pub_key_path
        os.environ['JWT_PRIVATE_KEY_PATH'] = cls.priv_key_path

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.pub_key_path):
            os.remove(cls.pub_key_path)
        if os.path.exists(cls.priv_key_path):
            os.remove(cls.priv_key_path)

    def setUp(self):
        # Initialize container with real (but test-keyed) services
        from infra.providers import generate_tokens, validate_token, mock_authenticate
        from types import SimpleNamespace
        
        self.container = get_container()
        self.container.register('auth', SimpleNamespace(
            authenticate=mock_authenticate,
            generate_tokens=generate_tokens,
            validate_token=validate_token
        ))
        self.container.register('renderer', MagicMock())

    def test_full_auth_lifecycle(self):
        # 1. Login
        login_body = json.dumps({"username": "admin", "password": "password123"}).encode('utf-8')
        environ = {
            'REQUEST_METHOD': 'POST',
            'CONTENT_LENGTH': len(login_body),
            'wsgi.input': io.BytesIO(login_body),
            'HTTP_HOST': 'localhost'
        }
        start_response = MagicMock()
        login_result = login_app(environ, start_response)
        
        status = start_response.call_args[0][0]
        headers = start_response.call_args[0][1]
        self.assertEqual(status, '200 OK')
        
        # Extract cookies
        cookies = [v for k, v in headers if k == 'Set-Cookie']
        access_cookie = next(c for c in cookies if 'silo_token=' in c)
        refresh_cookie = next(c for c in cookies if 'refresh_token=' in c)
        
        access_token = access_cookie.split('silo_token=')[1].split(';')[0]
        refresh_token = refresh_cookie.split('refresh_token=')[1].split(';')[0]

        # 2. Access protected resource (Reports)
        environ = {
            'REQUEST_METHOD': 'GET',
            'HTTP_COOKIE': f'silo_token={access_token}',
            'PATH_INFO': '/reports'
        }
        start_response = MagicMock()
        reports_result = reports_app(environ, start_response)
        self.assertEqual(start_response.call_args[0][0], '200 OK')

        # 3. Refresh tokens
        environ = {
            'REQUEST_METHOD': 'POST',
            'HTTP_COOKIE': f'refresh_token={refresh_token}',
            'PATH_INFO': '/refresh'
        }
        start_response = MagicMock()
        refresh_result = refresh_app(environ, start_response)
        self.assertEqual(start_response.call_args[0][0], '200 OK')
        
        # Verify new tokens were issued
        new_cookies = [v for k, v in start_response.call_args[0][1] if k == 'Set-Cookie']
        self.assertTrue(any('silo_token=' in c for c in new_cookies))
        self.assertTrue(any('refresh_token=' in c for c in new_cookies))

if __name__ == '__main__':
    unittest.main()
