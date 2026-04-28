import unittest
from unittest.mock import MagicMock
import json
import io
from infra.middleware import json_body, json_response, _process_response

class TestInfra(unittest.TestCase):
    def test_json_body_decorator(self):
        @json_body
        def handler(environ, start_response, body=None, **kwargs):
            return body

        body_data = {"key": "value"}
        body_bytes = json.dumps(body_data).encode('utf-8')
        environ = {
            'CONTENT_LENGTH': str(len(body_bytes)),
            'wsgi.input': io.BytesIO(body_bytes)
        }
        start_response = MagicMock()
        
        result = handler(environ, start_response)
        self.assertEqual(result, body_data)

    def test_json_response_decorator_basic(self):
        @json_response
        def handler(environ, start_response, **kwargs):
            return {"foo": "bar"}

        environ = {}
        start_response = MagicMock()
        result = handler(environ, start_response)
        
        start_response.assert_called_once()
        self.assertEqual(start_response.call_args[0][0], '200 OK')
        self.assertEqual(json.loads(result[0].decode('utf-8')), {"foo": "bar"})

    def test_json_response_decorator_complex(self):
        @json_response
        def handler(environ, start_response, **kwargs):
            return {"status": "created"}, '201 Created', [('X-Test', 'Value')]

        environ = {}
        start_response = MagicMock()
        result = handler(environ, start_response)
        
        status = start_response.call_args[0][0]
        headers = start_response.call_args[0][1]
        
        self.assertEqual(status, '201 Created')
        self.assertIn(('X-Test', 'Value'), headers)
        self.assertEqual(json.loads(result[0].decode('utf-8')), {"status": "created"})

    def test_process_response_helper(self):
        # Case 1: Simple return
        body, status, headers = _process_response({"a": 1}, 'application/json')
        self.assertEqual(body, {"a": 1})
        self.assertEqual(status, '200 OK')
        self.assertEqual(headers, [('Content-Type', 'application/json')])

        # Case 2: Tuple return (body, status)
        body, status, headers = _process_response(({"b": 2}, '201 Created'), 'application/json')
        self.assertEqual(body, {"b": 2})
        self.assertEqual(status, '201 Created')

        # Case 3: Tuple return (body, status, headers)
        body, status, headers = _process_response(({"c": 3}, '400 Bad Request', [('X-Error', 'foo')]), 'application/json')
        self.assertEqual(body, {"c": 3})
        self.assertEqual(status, '400 Bad Request')
        self.assertIn(('X-Error', 'foo'), headers)

if __name__ == '__main__':
    unittest.main()
