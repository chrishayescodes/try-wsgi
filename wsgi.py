import yaml
import importlib.util
import os
import sys
import logging

# Set up logging for the router
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("router")

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
SOURCE_DIR = os.getcwd()

# Ensure SILO_DIR and SOURCE_DIR are in the path for imports
for path in [SILO_DIR, SOURCE_DIR]:
    if path not in sys.path:
        sys.path.append(path)

# Load manifest
with open(MANIFEST_PATH, 'r') as f:
    config = yaml.safe_load(f)

routes = {}

def load_handler(slug, handler_path, target_name):
    # 1. Try the deployment path first (flattened silo)
    module_path = os.path.join(SILO_DIR, f"{target_name}.py")
    
    # 2. Fallback to the original path (useful for local dev)
    if not os.path.exists(module_path) and handler_path:
        module_path = os.path.join(SOURCE_DIR, handler_path)
    
    if not os.path.exists(module_path):
        logger.error(f"Handler file for {slug} not found at {module_path}")
        return None
    
    try:
        spec = importlib.util.spec_from_file_location(target_name, module_path)
        if spec is None:
            raise ImportError(f"Could not create spec for {module_path}")
            
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if not hasattr(module, 'application'):
            raise AttributeError(f"Module {target_name} has no 'application' attribute")
            
        return module.application
    except Exception as e:
        logger.exception(f"Failed to load handler for {slug} from {module_path}: {str(e)}")
        return None

def error_500_handler(environ, start_response):
    start_response('500 Internal Server Error', [('Content-Type', 'text/plain')])
    return [b"Internal Server Error: Handler failed to load. Check logs."]

# Initialize routes
for endpoint in config['endpoints']:
    slug = endpoint.get('slug', '')
    handler_path = endpoint.get('handler')
    
    # Match bash logic: empty string or 'null' refers to the root handler
    if not slug or slug == 'null':
        slug = ''
        target_name = "root_home_silo"
    else:
        target_name = f"{slug}_silo"
    
    handler = load_handler(slug, handler_path, target_name)
    
    route_path = '/' + slug.lstrip('/')
    if handler:
        routes[route_path] = handler
    else:
        # Route exists in manifest but handler failed to load
        routes[route_path] = error_500_handler
        logger.warning(f"Route {route_path} registered with error handler due to load failure.")

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
        try:
            # Pass through to the actual application
            return handler(environ, start_response)
        except Exception as e:
            logger.exception(f"Runtime error in handler for {path}: {str(e)}")
            return error_500_handler(environ, start_response)
    
    start_response('404 Not Found', [('Content-Type', 'text/plain')])
    return [b"Not Found"]
