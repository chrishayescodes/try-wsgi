#!/bin/bash
SOURCE_DIR="/workspaces/try-apache"
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

# Ensure the web server user can access the keys in the mount
chown -R www-data:www-data /etc/jwt-keys
chmod 444 /etc/jwt-keys/*.pem

# Add this to postcreate.sh to ensure the directory is searchable by Apache
chmod 755 /etc/jwt-keys
chmod 644 /etc/jwt-keys/*.pem

# 2. Link Global Templates
ln -sf "$SOURCE_DIR/templates/"* "$SILO_DIR/"

# 3. Deploy Endpoints
echo "Deploying Endpoints..."
endpoint_config=""

endpoint_count=$(yq e '.endpoints | length' "$MANIFEST")
for ((i=0; i<$endpoint_count; i++)); do
    slug=$(yq e ".endpoints[$i].slug" "$MANIFEST" | xargs)
    handler=$(yq e ".endpoints[$i].handler" "$MANIFEST")
    template=$(yq e ".endpoints[$i].template" "$MANIFEST") # <--- ADD THIS
    
    # 1. Handle Handler renaming for Root vs Slugs
    if [ -z "$slug" ] || [ "$slug" == "null" ]; then
        target_filename="root_home_silo.py"
        url_path="/"
    else
        target_filename="${slug}_silo.py"
        url_path="/$slug"
    fi
    
    ln -sf "$SOURCE_DIR/$handler" "$SILO_DIR/$target_filename"
    
    # 2. THE FIX: Link the feature-specific template into the flat silo root
    if [ "$template" != "null" ]; then
        ln -sf "$SOURCE_DIR/$template" "$SILO_DIR/$(basename $template)"
        echo "Linked Template: $(basename $template)"
    fi
    
    # 3. Build Apache Route
    ROUTES_CONFIG="$ROUTES_CONFIG
    WSGIScriptAlias $url_path $SILO_DIR/$target_filename"
    
    dos2unix "$SOURCE_DIR/$handler"
    chmod +x "$SOURCE_DIR/$handler"
done

# 4. Generate Apache Config
# ... (inside postcreate.sh) ...

# Generate Apache Config
cat <<EOF > /etc/apache2/sites-available/000-default.conf
WSGIPythonPath $SILO_DIR
<VirtualHost *:80>
    # SECURE PATHS: Outside of the /var/www/ web root
    SetEnv JWT_PUBLIC_KEY_PATH /etc/jwt-keys/jwt-public.pem
    SetEnv JWT_PRIVATE_KEY_PATH /etc/jwt-keys/jwt-private.pem

    DocumentRoot /var/www/html
    
    WSGIDaemonProcess python_silo processes=2 threads=15 python-path=$SILO_DIR
    WSGIProcessGroup python_silo
    WSGIApplicationGroup %{GLOBAL}

    $ROUTES_CONFIG
    <Directory $SILO_DIR>
        Options +FollowSymLinks
        Require all denied
        # CRITICAL: Only allow execution/reading of py and html
        # No more .pem files allowed here!
        <FilesMatch "\.(py|html)$">
            Require all granted
        </FilesMatch>
    </Directory>
</VirtualHost>
EOF

apache2ctl -k graceful