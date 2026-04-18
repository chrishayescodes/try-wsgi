import jwt
import datetime
import json
import os

# Configuration
PRIVATE_KEY_PATH = "/var/www/silos/jwt-private.pem"

def application(environ, start_response):
    # 1. Only allow POST requests
    if environ.get('REQUEST_METHOD') != 'POST':
        start_response('405 Method Not Allowed', [('Content-Type', 'text/plain')])
        return [b"Method Not Allowed"]

    try:
        # 2. Read the raw input stream from the request body
        try:
            request_body_size = int(environ.get('CONTENT_LENGTH', 0))
        except (ValueError):
            request_body_size = 0
            
        request_body = environ['wsgi.input'].read(request_body_size)
        
        # 3. Deserialize JSON to Python Dict
        data = json.loads(request_body)
        
        # 4. Extract variables (This fixes your NameError!)
        username = data.get('username')
        password = data.get('password')

        # 5. Credential Check
        if username == "admin" and password == "password123":
            # Load Private Key for signing
            with open(PRIVATE_KEY_PATH, 'r') as f:
                private_key = f.read()

            # Create JWT Claims
            payload = {
                "sub": "1234567890",
                "name": "Admin User",
                "iat": datetime.datetime.utcnow(),
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
            }
            
            # Sign the token
            token = jwt.encode(payload, private_key, algorithm="RS256")

            # 6. Set the HttpOnly Cookie
            # Note: We use 'silo_token' as the key for our middleware to find
            cookie_value = f"silo_token={token}; Path=/; HttpOnly; SameSite=Strict"

            headers = [
                ('Content-Type', 'application/json'),
                ('Set-Cookie', cookie_value)
            ]
            
            start_response('200 OK', headers)
            return [json.dumps({"status": "success", "message": "Logged in"}).encode('utf-8')]

        else:
            # Failed Login
            start_response('401 Unauthorized', [('Content-Type', 'application/json')])
            return [json.dumps({"status": "error", "error": "Invalid credentials"}).encode('utf-8')]

    except Exception as e:
        # Log the error to Apache logs and return a 500
        print(f"CRITICAL LOGIN ERROR: {str(e)}", file=environ['wsgi.errors'])
        start_response('500 Internal Server Error', [('Content-Type', 'text/plain')])
        return [f"Server Error: {str(e)}".encode('utf-8')]