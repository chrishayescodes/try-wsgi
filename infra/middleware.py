import functools
import os
import urllib.parse
import json
from infra.providers import get_container


def allowverbs(*verbs):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(environ, start_response, **kwargs):
            if environ.get('REQUEST_METHOD') not in verbs:
                start_response('405 Method Not Allowed', [('Content-Type', 'text/plain')])
                return [b"Method Not Allowed"]
            return func(environ, start_response, **kwargs)
        return wrapper
    return decorator


def inject_template(func):
    @functools.wraps(func)
    def wrapper(environ, start_response, **kwargs):
        container = get_container()
        kwargs['renderer'] = container.resolve('renderer')
        return func(environ, start_response, **kwargs)
    return wrapper


def inject_params(func):
    @functools.wraps(func)
    def wrapper(environ, start_response, **kwargs):
        query_string = environ.get('QUERY_STRING', '')
        params = urllib.parse.parse_qs(query_string)
        flat_params = {k: v[0] if v else None for k, v in params.items()}
        kwargs['params'] = flat_params
        return func(environ, start_response, **kwargs)
    return wrapper


def json_body(func):
    """Parses JSON from the request body and injects it into kwargs."""
    @functools.wraps(func)
    def wrapper(environ, start_response, **kwargs):
        try:
            content_length = int(environ.get('CONTENT_LENGTH', 0))
            if content_length > 0:
                body = environ['wsgi.input'].read(content_length)
                kwargs['body'] = json.loads(body)
            else:
                kwargs['body'] = {}
        except (ValueError, json.JSONDecodeError):
            start_response('400 Bad Request', [('Content-Type', 'text/plain')])
            return [b"Invalid JSON body"]
        
        return func(environ, start_response, **kwargs)
    return wrapper


def _process_response(result, default_content_type):
    """Helper to normalize handler return values."""
    status = '200 OK'
    headers = [('Content-Type', default_content_type)]
    body = result

    if isinstance(result, tuple):
        if len(result) >= 1:
            body = result[0]
        if len(result) >= 2:
            status = result[1]
        if len(result) >= 3:
            headers.extend(result[2])
    
    return body, status, headers


def json_response(func):
    @functools.wraps(func)
    def wrapper(environ, start_response, **kwargs):
        result = func(environ, start_response, **kwargs)
        if isinstance(result, list):
            return result
            
        body, status, headers = _process_response(result, 'application/json')
        
        start_response(status, headers)
        if isinstance(body, (dict, list)):
            return [json.dumps(body).encode('utf-8')]
        if isinstance(body, str):
            return [body.encode('utf-8')]
        return [body]
    return wrapper


def html_response(func):
    @functools.wraps(func)
    def wrapper(environ, start_response, **kwargs):
        result = func(environ, start_response, **kwargs)
        if isinstance(result, list):
            return result
            
        body, status, headers = _process_response(result, 'text/html')

        start_response(status, headers)
        if isinstance(body, str):
            return [body.encode('utf-8')]
        return [body]
    return wrapper
