#!/bin/bash
# ============================================================================
# SuryaGrid — Setup subdomain (suryagrid.mithungowda.in)
# Run this ON the EC2 instance after deploy.sh
# ============================================================================

set -e

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  Setting up suryagrid.mithungowda.in        ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ---------- 1. Create Nginx site config ----------
echo "[1/4] Creating Nginx config..."

sudo tee /etc/nginx/sites-available/suryagrid > /dev/null <<'EOF'
server {
    listen 80;
    server_name suryagrid.mithungowda.in;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_cache_bypass $http_upgrade;
    }

    location /api/ {
        proxy_pass http://localhost:8080/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
EOF

echo "  ✓ Config written"

# ---------- 2. Enable site ----------
echo "[2/4] Enabling site..."
sudo ln -sf /etc/nginx/sites-available/suryagrid /etc/nginx/sites-enabled/suryagrid

# ---------- 3. Test & reload Nginx ----------
echo "[3/4] Testing Nginx config..."
sudo nginx -t
sudo systemctl reload nginx
echo "  ✓ Nginx reloaded"

# ---------- 4. Pull latest code & rebuild containers ----------
echo "[4/4] Rebuilding containers..."
cd ~/SuryaGrid
git pull origin main
docker compose down
docker compose up --build -d

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║          ✓ SETUP COMPLETE!                   ║"
echo "╠══════════════════════════════════════════════╣"
echo "║                                              ║"
echo "║  http://suryagrid.mithungowda.in             ║"
echo "║  http://suryagrid.mithungowda.in/api/v1/health ║"
echo "║                                              ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
