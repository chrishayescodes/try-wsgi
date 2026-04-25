import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import json
import io

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../endpoints/auth')))

from endpoints.auth.login import application
from infra.providers import get_container, AuthProvider

class TestAuthSilo(unittest.TestCase):

    def test_login_success(self):
        # 1. Setup Mock Auth Provider
        mock_auth = MagicMock(spec=AuthProvider)
        mock_auth.authenticate.return_value = {"sub": "user123", "name": "Test User"}
        mock_auth.generate_tokens.return_value = ("access_val", "refresh_val")
        
        # 2. Register mock in container
        container = get_container()
        container.register('auth', mock_auth)
        
        # Mock renderer too
        mock_renderer = MagicMock()
        container.register('renderer', mock_renderer)

        # 3. Setup WSGI mocks for POST
        body = json.dumps({"username": "test", "password": "pass"}).encode('utf-8')
        environ = {
            'REQUEST_METHOD': 'POST',
            'CONTENT_LENGTH': len(body),
            'wsgi.input': io.BytesIO(body)
        }
        start_response = MagicMock()

        # 4. Call application
        result = application(environ, start_response)

        # 5. Assertions
        status_code = start_response.call_args[0][0]
        self.assertEqual(status_code, '200 OK')
        
        response_data = json.loads(result[0].decode('utf-8'))
        self.assertEqual(response_data['status'], 'success')
        
        mock_auth.authenticate.assert_called_with('test', 'pass')

    def test_login_failure(self):
        # 1. Setup Mock Auth Provider
        mock_auth = MagicMock(spec=AuthProvider)
        mock_auth.authenticate.return_value = None
        
        # 2. Register mock in container
        container = get_container()
        container.register('auth', mock_auth)

        # 3. Setup WSGI mocks for POST
        body = json.dumps({"username": "bad", "password": "bad"}).encode('utf-8')
        environ = {
            'REQUEST_METHOD': 'POST',
            'CONTENT_LENGTH': len(body),
            'wsgi.input': io.BytesIO(body)
        }
        start_response = MagicMock()

        # 4. Call application
        result = application(environ, start_response)

        # 5. Assertions
        status_code = start_response.call_args[0][0]
        self.assertEqual(status_code, '401 Unauthorized')
        
        response_data = json.loads(result[0].decode('utf-8'))
        self.assertEqual(response_data['status'], 'error')

if __name__ == '__main__':
    unittest.main()
