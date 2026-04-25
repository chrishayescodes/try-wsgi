#!/bin/bash
SOURCE_DIR="$(pwd)"
SILO_DIR="/var/www/silos"
MANIFEST="$SOURCE_DIR/manifest.yaml"

mkdir -p "$SILO_DIR"

# 1. Link Infrastructure (Libraries/Keys)
echo "Deploying Infrastructure..."
yq e '.infrastructure[].path' "$MANIFEST" | while read path; do
    # Only link if the file actually exists and isn't a pem file
    if [[ -f "$SOURCE_DIR/$path" && "$path" != *.pem ]]; then
        ln -sf "$SOURCE_DIR/$path" "$SILO_DIR/$(basename $path)"
    fi
done

# Only try to change permissions if the mount is writable
if touch /etc/jwt-keys/.p-test 2>/dev/null; then
    chown -R www-data:www-data /etc/jwt-keys
    chmod 444 /etc/jwt-keys/*.pem
    chmod 755 /etc/jwt-keys
    rm /etc/jwt-keys/.p-test
else
    echo "Notice: /etc/jwt-keys is read-only, skipping permission changes."
fi

# 2. Link Global Templates
ln -sf "$SOURCE_DIR/templates/"* "$SILO_DIR/"

# 3. Deploy Endpoints
echo "Deploying Endpoints..."

endpoint_count=$(yq e '.endpoints | length' "$MANIFEST")
for ((i=0; i<$endpoint_count; i++)); do
    slug=$(yq e ".endpoints[$i].slug" "$MANIFEST" | xargs)
    handler=$(yq e ".endpoints[$i].handler" "$MANIFEST")
    template=$(yq e ".endpoints[$i].template" "$MANIFEST")
    
    # 1. Handle Handler renaming for Root vs Slugs
    if [ -z "$slug" ] || [ "$slug" == "null" ]; then
        target_filename="root_home_silo.py"
    else
        target_filename="${slug}_silo.py"
    fi
    
    ln -sf "$SOURCE_DIR/$handler" "$SILO_DIR/$target_filename"
    
    # 2. Link the feature-specific template into the flat silo root
    if [ "$template" != "null" ]; then
        ln -sf "$SOURCE_DIR/$template" "$SILO_DIR/$(basename $template)"
        echo "Linked Template: $(basename $template)"
    fi
    
    dos2unix "$SOURCE_DIR/$handler"
    chmod +x "$SOURCE_DIR/$handler"
done

# 4. Link the WSGI router
ln -sf "$SOURCE_DIR/wsgi.py" "$SILO_DIR/wsgi.py"

# 5. Generate Nginx Config
cp "$SOURCE_DIR/nginx-silo.conf" /etc/nginx/sites-available/default

# 6. Start/Restart services
echo "Starting Nginx..."
service nginx start || service nginx restart

# Set environment variables for Gunicorn
export JWT_PUBLIC_KEY_PATH=/etc/jwt-keys/jwt-public.pem
export JWT_PRIVATE_KEY_PATH=/etc/jwt-keys/jwt-private.pem
export JWT_ACCESS_EXP_SECONDS=15

# Start Gunicorn
echo "Starting Gunicorn..."
pkill gunicorn || true
cd /var/www/silos

# Base Gunicorn command
GUNICORN_CMD="gunicorn --bind 0.0.0.0:8000 wsgi:application --daemon --access-logfile /var/log/gunicorn-access.log --error-logfile /var/log/gunicorn-error.log"

# Add debug flags if DEBUG env var is set to true
if [ "$DEBUG" = "true" ]; then
    echo "Debug mode enabled: capturing output and setting log level to debug."
    GUNICORN_CMD="$GUNICORN_CMD --capture-output --log-level debug"
fi

# Execute Gunicorn
$GUNICORN_CMD

echo "Deployment complete."