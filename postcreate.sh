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
cat <<EOF > "$APACHE_CONF"
<VirtualHost *:80>
    DocumentRoot /var/www/html
    
    WSGIPythonPath /var/www/silos
    WSGIDaemonProcess python_silo processes=2 threads=15
    WSGIProcessGroup python_silo
    WSGIApplicationGroup %{GLOBAL}

    # --- DYNAMIC ROUTES START ---
    $ROUTES_CONFIG
    # --- DYNAMIC ROUTES END ---

    <Directory $SILO_DIR>
        Require all granted
    </Directory>

    <Directory /var/www/html>
        Options -Indexes
        Require all granted
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