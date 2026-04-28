#!/bin/sh
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
SECRETS_DIR="$BASE_DIR/secrets"
PRIVATE_KEY="$SECRETS_DIR/jwt-private.pem"
PUBLIC_KEY="$SECRETS_DIR/jwt-public.pem"

mkdir -p "$SECRETS_DIR"

if [ -f "$PRIVATE_KEY" ] && [ -f "$PUBLIC_KEY" ]; then
  echo "JWT secret files already exist in $SECRETS_DIR"
  exit 0
fi

echo "Creating JWT secret files in $SECRETS_DIR"

if command -v openssl >/dev/null 2>&1; then
  if [ ! -f "$PRIVATE_KEY" ]; then
    openssl genpkey -algorithm RSA -out "$PRIVATE_KEY" -pkeyopt rsa_keygen_bits:2048
    chmod 600 "$PRIVATE_KEY"
  fi

  if [ ! -f "$PUBLIC_KEY" ]; then
    openssl rsa -pubout -in "$PRIVATE_KEY" -out "$PUBLIC_KEY"
    chmod 644 "$PUBLIC_KEY"
  fi

  echo "Created $PRIVATE_KEY and $PUBLIC_KEY"
else
  cat > "$PRIVATE_KEY" <<'EOF'
-----BEGIN RSA PRIVATE KEY-----
PLACEHOLDER_PRIVATE_KEY
-----END RSA PRIVATE KEY-----
EOF
  chmod 600 "$PRIVATE_KEY"

  cat > "$PUBLIC_KEY" <<'EOF'
-----BEGIN PUBLIC KEY-----
PLACEHOLDER_PUBLIC_KEY
-----END PUBLIC KEY-----
EOF
  chmod 644 "$PUBLIC_KEY"

  echo "openssl not available; created placeholder files at $SECRETS_DIR"
fi
