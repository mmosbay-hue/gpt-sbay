#!/bin/bash
# Deploy GPT Web SaaS — chạy trên VPS
# Usage: bash deploy.sh yourdomain.com

DOMAIN=${1:-"localhost"}

echo "=== GPT Web Deploy ==="
echo "Domain: $DOMAIN"

# 1. Copy .env
if [ ! -f .env ]; then
    cp .env.example .env
    echo ">>> Tạo .env — SẾP CẦN ĐIỀN API KEYS VÀO FILE .env <<<"
    exit 1
fi

# 2. Update nginx config with domain
sed -i "s/server_name _;/server_name $DOMAIN;/" nginx.conf

# 3. Build & start
docker compose up -d --build

# 4. Wait for app
sleep 10

# 5. SSL certificate (nếu có domain thật)
if [ "$DOMAIN" != "localhost" ]; then
    docker compose run --rm certbot certonly --webroot -w /var/www/certbot -d $DOMAIN --non-interactive --agree-tos -m admin@$DOMAIN

    # Add SSL to nginx
    cat > nginx.conf << 'NGINX'
server {
    listen 80;
    server_name DOMAIN_PLACEHOLDER;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 301 https://$host$request_uri; }
}
server {
    listen 443 ssl;
    server_name DOMAIN_PLACEHOLDER;
    ssl_certificate /etc/letsencrypt/live/DOMAIN_PLACEHOLDER/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/DOMAIN_PLACEHOLDER/privkey.pem;
    location / {
        proxy_pass http://app:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_read_timeout 300s;
    }
}
NGINX
    sed -i "s/DOMAIN_PLACEHOLDER/$DOMAIN/g" nginx.conf
    docker compose restart nginx
fi

# 6. Seed admin
docker compose exec app python -m backend.db.seed

echo ""
echo "=== DONE ==="
echo "URL: http://$DOMAIN"
echo "Admin: email/password theo ADMIN_EMAIL / ADMIN_PASSWORD trong .env"
echo ""
echo ">>> NHỚ ĐỔI MẬT KHẨU ADMIN <<<"
