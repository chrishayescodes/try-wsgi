import yaml
import importlib.util
import os
import sys

# Path to the manifest file - check common locations
MANIFEST_LOCATIONS = [
    '/workspaces/try-apache/manifest.yaml',
    '/var/www/silos/manifest.yaml',
    os.path.join(os.getcwd(), 'manifest.yaml')
]
MANIFEST_PATH = next((p for p in MANIFEST_LOCATIONS if os.path.exists(p)), None)

if not MANIFEST_PATH:
    raise FileNotFoundError(f"Could not find manifest.yaml in {MANIFEST_LOCATIONS}")

SILO_DIR = '/var/www/silos'

# Ensure SILO_DIR is in the path for imports
if SILO_DIR not in sys.path:
    sys.path.append(SILO_DIR)

# Load manifest
with open(MANIFEST_PATH, 'r') as f:
    config = yaml.safe_load(f)

routes = {}

def load_handler(slug, target_name):
    module_path = os.path.join(SILO_DIR, f"{target_name}.py")
    if not os.path.exists(module_path):
        print(f"Warning: Handler for {slug} not found at {module_path}")
        return None
    
    spec = importlib.util.spec_from_file_location(target_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.application

# Initialize routes
for endpoint in config['endpoints']:
    slug = endpoint.get('slug')
    # Match bash logic: empty string or 'null' refers to the root handler
    if not slug or slug == 'null':
        slug = ''
        target_name = "root_home_silo"
    else:
        target_name = f"{slug}_silo"
    
    handler = load_handler(slug, target_name)
    if handler:
        routes['/' + slug.lstrip('/')] = handler

def application(environ, start_response):
    path = environ.get('PATH_INFO', '')
    # Normalize path: remove trailing slash if it's not the root
    if path != '/' and path.endswith('/'):
        path = path[:-1]
    
    # Try exact match
    handler = routes.get(path)
    
    # Try match without leading slash if path is empty (root)
    if not handler and path == '':
        handler = routes.get('/')

    if handler:
        # Pass through to the actual application
        return handler(environ, start_response)
    
    start_response('404 Not Found', [('Content-Type', 'text/plain')])
    return [b"Not Found"]
