#!/bin/bash
SOURCE_DIR="/workspaces/try-apache"
SILO_DIR="/var/www/silos"
MANIFEST="$SOURCE_DIR/manifest.yaml"

mkdir -p "$SILO_DIR"

# 1. Link Infrastructure (Libraries/Keys)
# We flatten these into the silo root so imports work simply
echo "Deploying Infrastructure..."
yq e '.infrastructure[].path' "$MANIFEST" | while read path; do
    ln -sf "$SOURCE_DIR/$path" "$SILO_DIR/$(basename $path)"
done

# 2. Link Global Templates
ln -sf "$SOURCE_DIR/templates/"* "$SILO_DIR/"

# 3. Deploy Endpoints
echo "Deploying Endpoints..."
ROUTES_CONFIG=""

# Loop through endpoints in YAML
endpoint_count=$(yq e '.endpoints | length' "$MANIFEST")
for ((i=0; i<$endpoint_count; i++)); do
    slug=$(yq e ".endpoints[$i].slug" "$MANIFEST")
    handler=$(yq e ".endpoints[$i].handler" "$MANIFEST")
    template=$(yq e ".endpoints[$i].template" "$MANIFEST")
    
    # We rename the handler to include the slug to avoid 'index.py' collisions
    # e.g. endpoints/home/index.py -> /var/www/silos/home_silo.py
    target_filename="${slug}_silo.py"
    ln -sf "$SOURCE_DIR/$handler" "$SILO_DIR/$target_filename"
    
    # Link the specific template with a unique name
    target_template="${slug}_template.html"
    ln -sf "$SOURCE_DIR/$template" "$SILO_DIR/$target_template"
    
    # Build Apache Route
    ROUTES_CONFIG="$ROUTES_CONFIG
    WSGIScriptAlias /api/$slug $SILO_DIR/$target_filename"
    
    dos2unix "$SOURCE_DIR/$handler"
    chmod +x "$SOURCE_DIR/$handler"
done

# 4. Generate Apache Config
cat <<EOF > /etc/apache2/sites-available/000-default.conf
WSGIPythonPath $SILO_DIR
<VirtualHost *:80>
    SetEnv JWT_PUBLIC_KEY_PATH /var/www/silos/jwt-public.pem
    DocumentRoot /var/www/html

    WSGIDaemonProcess python_silo processes=2 threads=15 python-path=$SILO_DIR
    WSGIProcessGroup python_silo
    WSGIApplicationGroup %{GLOBAL}

    $ROUTES_CONFIG

    <Directory $SILO_DIR>
        Options +FollowSymLinks
        Require all denied
        <FilesMatch "\.(py|html|pem)$">
            Require all granted
        </FilesMatch>
    </Directory>
</VirtualHost>
EOF

apache2ctl -k graceful