#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
#  RAG Tutor — Oracle Cloud Always Free Deployment Script
# ═══════════════════════════════════════════════════════════════════════
#  Run this AFTER SSH-ing into your Oracle Cloud VM:
#    ssh -i ~/.ssh/oci_key ubuntu@<YOUR_VM_IP>
#
#  Then run:
#    chmod +x deploy.sh && ./deploy.sh
# ═══════════════════════════════════════════════════════════════════════

set -e  # Exit on any error

echo "═══════════════════════════════════════════"
echo "  RAG Tutor — Oracle Cloud Setup"
echo "═══════════════════════════════════════════"

# ── 1. System update ──────────────────────────────────────────────────
echo ""
echo "[1/7] Updating system packages..."
sudo apt-get update && sudo apt-get upgrade -y

# ── 2. Install Docker ─────────────────────────────────────────────────
echo ""
echo "[2/7] Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker $USER
    echo "  ✓ Docker installed. You may need to log out and back in for group changes."
else
    echo "  ✓ Docker already installed"
fi

# ── 3. Install Docker Compose ─────────────────────────────────────────
echo ""
echo "[3/7] Installing Docker Compose..."
if ! command -v docker compose &> /dev/null; then
    sudo apt-get install -y docker-compose-plugin
    echo "  ✓ Docker Compose installed"
else
    echo "  ✓ Docker Compose already installed"
fi

# ── 4. Clone the repository ──────────────────────────────────────────
echo ""
echo "[4/7] Cloning repository..."
cd ~
if [ -d "Flask-CRUD-RAG-LLM" ]; then
    echo "  → Repo already exists, pulling latest..."
    cd Flask-CRUD-RAG-LLM
    git pull origin main
else
    git clone https://github.com/shivendra911/Flask-CRUD-RAG-LLM.git
    cd Flask-CRUD-RAG-LLM
fi

# ── 5. Create .env file ──────────────────────────────────────────────
echo ""
echo "[5/7] Setting up environment..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "  ⚠  IMPORTANT: Edit .env and add your GEMINI_API_KEY:"
    echo "     nano .env"
    echo ""
    read -p "  Press Enter after you've added your API key to .env..."
else
    echo "  ✓ .env already exists"
fi

# ── 6. Build and start with Docker ───────────────────────────────────
echo ""
echo "[6/7] Building and starting the app..."
sudo docker compose up -d --build

echo ""
echo "[6/7] Waiting for app to start..."
sleep 5

# Check if running
if sudo docker compose ps | grep -q "running"; then
    echo "  ✓ App is running on port 5000"
else
    echo "  ✗ App failed to start. Check logs:"
    echo "    sudo docker compose logs"
    exit 1
fi

# ── 7. Install Nginx ─────────────────────────────────────────────────
echo ""
echo "[7/7] Installing and configuring Nginx..."
sudo apt-get install -y nginx

# Create Nginx config
sudo tee /etc/nginx/sites-available/flask-rag > /dev/null <<'NGINX'
# ── Rate limiting zone ──────────────────────────────────────
# 10m = ~160,000 IPs tracked, 10r/m = 1 request per 6 seconds
limit_req_zone $binary_remote_addr zone=chat_limit:10m rate=10r/m;

server {
    listen 80;
    server_name _;   # Accepts any hostname (replace with domain later)

    # Must match Flask MAX_CONTENT_LENGTH (20MB)
    client_max_body_size 20M;

    # ── Chat route — rate limited ────────────────────────
    location /chat {
        limit_req zone=chat_limit burst=5 nodelay;
        limit_req_status 429;

        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    # ── All other routes ─────────────────────────────────
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
NGINX

# Enable the site
sudo ln -sf /etc/nginx/sites-available/flask-rag /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test and reload Nginx
sudo nginx -t && sudo systemctl reload nginx

echo ""
echo "═══════════════════════════════════════════"
echo "  ✅ DEPLOYMENT COMPLETE!"
echo "═══════════════════════════════════════════"
echo ""
echo "  Your app is live at: http://$(curl -s ifconfig.me)"
echo ""
echo "  Next steps:"
echo "  1. Open port 80 in Oracle Cloud Security List"
echo "  2. Open port 443 for HTTPS"
echo "  3. Run: sudo iptables -I INPUT 6 -p tcp --dport 80 -j ACCEPT"
echo "  4. Run: sudo iptables -I INPUT 6 -p tcp --dport 443 -j ACCEPT"
echo "  5. Save: sudo netfilter-persistent save"
echo ""
echo "  For HTTPS (after adding a domain):"
echo "  sudo apt install certbot python3-certbot-nginx"
echo "  sudo certbot --nginx -d your-domain.com"
echo ""
echo "  View logs:  sudo docker compose logs -f"
echo "  Restart:    sudo docker compose restart"
echo "  Stop:       sudo docker compose down"
echo ""
