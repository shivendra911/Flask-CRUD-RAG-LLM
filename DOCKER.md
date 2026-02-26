# 🐳 Docker Deployment Guide

Complete guide to running **RAG Tutor** with Docker — locally or on a cloud VM.

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Docker | 20.10+ | [docs.docker.com/get-docker](https://docs.docker.com/get-docker/) |
| Docker Compose | v2+ | Included with Docker Desktop |
| Gemini API Key | — | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) (free) |

---

## Quick Start (Local)

```bash
# 1. Clone the repo
git clone https://github.com/shivendra911/Flask-CRUD-RAG-LLM.git
cd Flask-CRUD-RAG-LLM

# 2. Create your .env
cp .env.example .env
# Edit .env → add your GEMINI_API_KEY

# 3. Build & run
docker compose up -d --build
```

Visit **http://localhost:5000** — register, upload a PDF, and start chatting!

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | ✅ | Google Gemini API key for LLM & embeddings |
| `SECRET_KEY` | ✅ | Flask session secret — generate with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `FLASK_ENV` | ❌ | `development` (default) or `production` |
| `DATABASE_URL` | ❌ | PostgreSQL URL — defaults to SQLite if not set |

---

## Persistent Volumes

Docker Compose mounts three named volumes so your data survives container restarts:

| Volume | Container Path | Contents |
|--------|---------------|----------|
| `uploads_data` | `/app/app/uploads` | User-uploaded PDF/TXT/MD files |
| `vector_data` | `/app/vector_store` | FAISS vector index |
| `sqlite_data` | `/app/instance` | SQLite database |

> **Tip:** To back up your data, use `docker compose cp web:/app/instance ./backup/`

---

## Common Commands

```bash
# View logs (follow mode)
docker compose logs -f

# Restart the app
docker compose restart

# Rebuild after code changes
docker compose up -d --build

# Stop everything
docker compose down

# Stop & remove all data (⚠ destructive)
docker compose down -v
```

---

## Production Deployment (Cloud VM)

### 1. Server Setup

SSH into your VM (Ubuntu 22.04+ recommended):

```bash
# Install Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# Install Docker Compose plugin
sudo apt-get install -y docker-compose-plugin

# Log out & back in for group changes
exit
```

### 2. Deploy the App

```bash
# Clone & configure
git clone https://github.com/shivendra911/Flask-CRUD-RAG-LLM.git
cd Flask-CRUD-RAG-LLM
cp .env.example .env
nano .env  # Add your GEMINI_API_KEY and a strong SECRET_KEY

# Build & start
docker compose up -d --build
```

### 3. Set Up Nginx Reverse Proxy

```bash
sudo apt-get install -y nginx
```

Create `/etc/nginx/sites-available/ragtutor`:

```nginx
# Add this to /etc/nginx/nginx.conf inside the http {} block:
# limit_req_zone $binary_remote_addr zone=chat_limit:10m rate=10r/m;

server {
    listen 80;
    server_name your-domain.com;  # ← Replace with your domain or _

    client_max_body_size 20M;

    # Chat route — rate limited
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

    # All other routes
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
```

Enable and start:

```bash
sudo ln -sf /etc/nginx/sites-available/ragtutor /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

### 4. Enable HTTPS (Optional)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 5. Firewall (Oracle Cloud / AWS)

```bash
# Open HTTP & HTTPS ports
sudo iptables -I INPUT 6 -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

Also open ports **80** and **443** in your cloud provider's Security List / Security Group.

---

## Sharing via Docker Hub

```bash
# Build the image
docker build -t your-dockerhub-username/rag-tutor:latest .

# Push to Docker Hub
docker login
docker push your-dockerhub-username/rag-tutor:latest

# Others can then run:
docker pull your-dockerhub-username/rag-tutor:latest
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Container exits immediately | Run `docker compose logs` to see the error |
| Port 5000 already in use | Change the port mapping in `docker-compose.yml` (e.g., `8080:5000`) |
| API rate limit errors | Check your Gemini API key quota at [aistudio.google.com](https://aistudio.google.com) |
| Upload fails (413) | Ensure `client_max_body_size` in Nginx matches Flask's `MAX_CONTENT_LENGTH` (20 MB) |
| Slow first response | The first query downloads the embedding model (~400 MB) — subsequent queries are fast |
| Data lost after rebuild | Make sure you're using `docker compose up`, not `docker compose down -v` |
