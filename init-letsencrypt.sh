#!/bin/bash
# Initial Let's Encrypt certificate acquisition for OHDSI Dashboard
# Run this ONCE on first deployment, then certbot container handles renewals.
#
# Usage: ./init-letsencrypt.sh [--staging]
#   --staging: Use Let's Encrypt staging server (for testing, avoids rate limits)

set -e

DOMAINS="ohdsihub.eastus2.cloudapp.azure.com"
EMAIL="admin@ohdsi.org"  # Change to your email for renewal notifications
COMPOSE_FILE="docker-compose.prod.yml"

# Use staging server if --staging flag is passed
STAGING_ARG=""
if [ "$1" = "--staging" ]; then
    STAGING_ARG="--staging"
    echo "Using Let's Encrypt STAGING server (certs won't be trusted by browsers)"
fi

echo "=== OHDSI Dashboard - Let's Encrypt Setup ==="
echo "Domain: $DOMAINS"
echo "Email: $EMAIL"
echo ""

# Step 1: Create a temporary nginx config for HTTP-only (cert acquisition)
echo "[1/4] Creating temporary HTTP-only nginx config..."
cat > /tmp/nginx-certbot-init.conf << 'NGINX_CONF'
events { worker_connections 1024; }
http {
    server {
        listen 80;
        server_name dash.ohdsi.org ohdsihub.eastus2.cloudapp.azure.com;

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 200 'OHDSI Dashboard - Setting up SSL...';
            add_header Content-Type text/plain;
        }
    }
}
NGINX_CONF

# Step 2: Start nginx with temporary config
echo "[2/4] Starting nginx with HTTP-only config..."
docker rm -f ohdsi-nginx-init 2>/dev/null || true

# Create named volumes if they don't exist
docker volume create certbot_webroot 2>/dev/null || true
docker volume create certbot_certs 2>/dev/null || true

docker run -d --name ohdsi-nginx-init \
    -v /tmp/nginx-certbot-init.conf:/etc/nginx/nginx.conf:ro \
    -v certbot_webroot:/var/www/certbot \
    -p 80:80 \
    nginx:1.25-alpine

sleep 3

# Verify nginx is running
if ! docker ps | grep -q ohdsi-nginx-init; then
    echo "ERROR: nginx failed to start. Check: docker logs ohdsi-nginx-init"
    exit 1
fi

echo "Nginx is running on port 80."

# Step 3: Request certificate
echo "[3/4] Requesting Let's Encrypt certificate..."
docker run --rm \
    -v certbot_webroot:/var/www/certbot \
    -v certbot_certs:/etc/letsencrypt \
    certbot/certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAINS" \
    $STAGING_ARG

# Step 4: Clean up temporary nginx
echo "[4/4] Cleaning up..."
docker stop ohdsi-nginx-init 2>/dev/null
docker rm ohdsi-nginx-init 2>/dev/null
rm -f /tmp/nginx-certbot-init.conf

echo ""
echo "=== Certificate obtained successfully! ==="
echo "Now start the full stack with:"
echo "  docker compose -f $COMPOSE_FILE up -d --build"
echo ""
echo "The certbot container will auto-renew certificates every 12 hours."
echo "To force renewal: docker compose -f $COMPOSE_FILE exec certbot certbot renew --force-renewal"
