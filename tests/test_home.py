import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import datetime

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Also add endpoints/home to simulate silo environment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../endpoints/home')))
# Also add infra
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../infra')))

from endpoints.home.index import get_home_data, application
from infra.providers import get_container

class TestHomeSilo(unittest.TestCase):

    def test_get_home_data(self):
        """Test the pure logic function without any WSGI/DI overhead."""
        fixed_now = datetime.datetime(2023, 10, 27, 10, 0, 0)
        data = get_home_data(now=fixed_now)
        
        self.assertEqual(data['user_name'], "AdminUser")
        self.assertEqual(data['current_time'], "2023-10-27 10:00:00")
        self.assertTrue(data['is_morning'])

    def test_application_integration(self):
        """Test the WSGI application with a mocked renderer."""
        # 1. Setup Mock Renderer
        mock_renderer = MagicMock()
        mock_renderer.render.return_value = b"<html>Mocked Content</html>"
        
        # 2. Register mock in container
        container = get_container()
        container.register('renderer', mock_renderer)
        
        # 3. Setup WSGI mocks
        environ = {'REQUEST_METHOD': 'GET'}
        start_response = MagicMock()
        
        # 4. Call application
        result = application(environ, start_response)
        
        # 5. Assertions
        self.assertEqual(result, [b"<html>Mocked Content</html>"])
        start_response.assert_called_with('200 OK', [('Content-Type', 'text/html')])
        mock_renderer.render.assert_called_once()
        
        # Check that it passed correct data to render
        args, kwargs = mock_renderer.render.call_args
        self.assertEqual(args[0], 'index.html')
        self.assertEqual(args[1]['user_name'], "AdminUser")

if __name__ == '__main__':
    unittest.main()
