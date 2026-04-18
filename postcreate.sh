#!/bin/bash

# 1. Configuration
MANIFEST="scripts_manifest.txt"
SOURCE_DIR="/workspaces/try-apache"
SILO_DIR="/var/www/silos"
APACHE_CONF="/etc/apache2/sites-available/000-default.conf"

mkdir -p "$SILO_DIR"
echo "Starting Dynamic Deployment..."

# 2. Start building the new Apache Config string
# We use a variable to store the 'routing' part of the config
ROUTES_CONFIG=""
# Inside postcreate.sh
ln -sf /workspaces/try-apache/jwt-public.pem /var/www/silos/jwt-public.pem
if [ -f "$SOURCE_DIR/$MANIFEST" ]; then
    # Link all .html files so the templates are in the same folder as the scripts
    ln -sf /workspaces/try-apache/*.html /var/www/silos/
    while IFS= read -r filename || [ -n "$filename" ]; do
        # Trim whitespace
        filename=$(echo "$filename" | xargs)
        
        # 1. Skip empty lines (Standard [ ] syntax)
        if [ -z "$filename" ]; then continue; fi
        
        # 2. Skip comments starting with #
        case "$filename" in \#*) continue ;; esac

        if [ -f "$SOURCE_DIR/$filename" ]; then
            # Define the URL slug (hello.py becomes hello)
            slug="${filename%.*}"
            
            echo "Processing: $slug -> $filename"
            
            # Create the link
            ln -sf "$SOURCE_DIR/$filename" "$SILO_DIR/$filename"
            
            # Add to our routing config string (using a literal newline)
            ROUTES_CONFIG="$ROUTES_CONFIG
    WSGIScriptAlias /api/$slug $SILO_DIR/$filename"
            
            dos2unix "$SOURCE_DIR/$filename"
            chmod +x "$SOURCE_DIR/$filename"
        fi
    done < "$SOURCE_DIR/$MANIFEST"
fi

# 3. Rewrite the Apache VirtualHost file entirely
# This ensures the config is always fresh and matches the manifest
# ... inside postcreate.sh, after the loop builds $ROUTES_CONFIG ...

cat <<EOF > /etc/apache2/sites-available/000-default.conf
# This ensures silos can import theme.py or libraries in the same folder
WSGIPythonPath $SILO_DIR

<VirtualHost *:80>
    # The Silo looks for this variable to find its certificate
    SetEnv JWT_PUBLIC_KEY_PATH /var/www/silos/jwt-public.pem
    
    DocumentRoot /var/www/html

    # Warm-start Python Daemon
    WSGIDaemonProcess python_silo processes=2 threads=15
    WSGIProcessGroup python_silo
    WSGIApplicationGroup %{GLOBAL}
    

    # --- DYNAMICALLY GENERATED ROUTES ---
    $ROUTES_CONFIG
    # ------------------------------------

    <Directory /var/www/silos>
        # Secure the directory: Only allow WSGI access
        Require all denied
        <FilesMatch "\.(py|html)$">
            Require all granted
        </FilesMatch>
    </Directory>

    ErrorLog \${APACHE_LOG_DIR}/error.log
    CustomLog \${APACHE_LOG_DIR}/access.log combined
</VirtualHost>
EOF

# 4. Reload Apache to apply the new routes
echo "Reloading Apache..."
source /etc/apache2/envvars
apache2ctl -k graceful

echo "Deployment complete. Your silos are live!"