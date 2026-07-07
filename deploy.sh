#!/bin/bash
# ============================================================================
# SuryaGrid — Deploy to Ubuntu EC2/Lightsail (32.197.42.115)
# Usage: curl -sL <raw_url> | bash   OR   bash deploy.sh
# ============================================================================

set -e

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   SuryaGrid AI — Ubuntu Deploy Script   ║"
echo "╠══════════════════════════════════════════╣"
echo "║   Instance: 2GB RAM, 2 vCPUs            ║"
echo "║   IP: 32.197.42.115                     ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ---------- 1. System update ----------
echo "[1/7] Updating system packages..."
sudo apt update -y && sudo apt upgrade -y

# ---------- 2. Install Docker & Git ----------
echo "[2/7] Installing Docker & Git..."
sudo apt install -y docker.io docker-compose-v2 git curl
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# ---------- 3. Add swap (critical for 2GB RAM) ----------
echo "[3/7] Setting up 2GB swap..."
if [ ! -f /swapfile ]; then
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    echo "  ✓ Swap enabled"
else
    echo "  ✓ Swap already exists"
fi

# ---------- 4. Clone or pull repo ----------
echo "[4/7] Getting latest code..."
REPO_DIR="$HOME/SuryaGrid"

if [ -d "$REPO_DIR" ]; then
    cd "$REPO_DIR"
    git pull origin main
    echo "  ✓ Pulled latest"
else
    git clone https://github.com/DBIT-Banglore/SuryaGrid.git "$REPO_DIR"
    cd "$REPO_DIR"
    echo "  ✓ Cloned"
fi

# ---------- 5. Create .env ----------
echo "[5/7] Setting up environment..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "  ✓ .env created from template"
else
    echo "  ✓ .env already exists"
fi

# ---------- 6. Build and start containers ----------
echo "[6/7] Building and starting containers (this takes 5-10 min on first run)..."
sudo docker compose down 2>/dev/null || true
sudo docker compose up --build -d

# ---------- 7. Wait for health ----------
echo "[7/7] Waiting for services to start..."
echo ""

for i in {1..20}; do
    if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        echo ""
        echo "╔══════════════════════════════════════════╗"
        echo "║          ✓ DEPLOYMENT COMPLETE!          ║"
        echo "╠══════════════════════════════════════════╣"
        echo "║                                          ║"
        echo "║  Frontend:  http://32.197.42.115:3000    ║"
        echo "║  Backend:   http://32.197.42.115:8000    ║"
        echo "║  Swagger:   http://32.197.42.115:8000/docs║"
        echo "║                                          ║"
        echo "║  Logs:  docker compose logs -f           ║"
        echo "║  Stop:  docker compose down              ║"
        echo "║                                          ║"
        echo "╚══════════════════════════════════════════╝"
        echo ""
        exit 0
    fi
    printf "  Waiting... (%d/20)\r" "$i"
    sleep 5
done

echo ""
echo "⚠ Backend not responding yet. It may still be starting."
echo "  Check logs: sudo docker compose logs -f"
echo "  Check status: sudo docker compose ps"
echo ""
