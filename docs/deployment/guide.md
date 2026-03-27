# Chorus Agent Conflict Predictor - Comprehensive Deployment Guide

This guide covers deployment options for the Chorus Agent Conflict Predictor system, including quick starts, detailed configuration, and production strategies.

## 🚀 Quick Start

### Prerequisites
- **Gemini API Key**: [Get from Google AI Studio](https://makersuite.google.com/app/apikey)
- **Docker**: Installed and running (Recommended method)
- **Redis**: Required if running natively (included in Docker)

### Option 1: Docker Development (Fastest)

```bash
# 1. Navigate to backend
cd backend

# 2. Configure Environment
cp .env.example .env
# Edit .env and add your CHORUS_GEMINI_API_KEY
nano .env

# 3. Launch
./deploy-docker.sh dev

# 4. Access
# Dashboard: http://localhost:3000
# API: http://localhost:8000
```

### Option 2: Production Docker

```bash
# 1. Setup Production Config
cp .env.production .env
nano .env # Add keys and adjust settings

# 2. Deploy
./deploy-docker.sh prod

# 3. Validate
./validate-deployment.sh --backend-url http://localhost:8000
```

---

## 📋 Configuration Details

### 1. Environment Setup

Copy the appropriate template:
```bash
# For development
cp .env.example .env

# For production
cp .env.production .env
```

**Key Configuration Variables:**

| Variable | Description | Required |
|----------|-------------|----------|
| `CHORUS_ENVIRONMENT` | `production` or `development` | Yes |
| `CHORUS_GEMINI_API_KEY` | Google Gemini API Key | Yes |
| `CHORUS_REDIS_HOST` | Redis Hostname | Yes |
| `CHORUS_DATADOG_ENABLED`| Enable Datadog Observability | No |

### 2. Validation

Before fully deploying, validate your configuration:

```bash
python start_system.py validate-config
# or
python -m src.config_validator
```

---

## 🛠 Deployment Strategies

### 1. Docker Deployment (Standard)

The project includes a robust `deploy-docker.sh` script to manage containers.

**Commands:**
- `./deploy-docker.sh dev`: Start development stack (hot-reload).
- `./deploy-docker.sh prod`: Start production stack (optimized images, nginx).
- `./deploy-docker.sh status`: Check service health.
- `./deploy-docker.sh logs`: Tail logs.
- `./deploy-docker.sh stop`: Stop all services.

**Services Included:**
- `backend`: FastAPI application.
- `dashboard`: React frontend.
- `redis`: Persistence layer.
- `nginx`: Reverse proxy (Production only).

### 2. Kubernetes Deployment (Scalable)

For production clusters using `k8s-deployment.yml`.

```bash
# 1. Configure Secrets & ConfigMaps
# (Edit k8s-deployment.yml or use kubectl create secret)

# 2. Apply Manifests
kubectl apply -f k8s-deployment.yml

# 3. Verify
kubectl get pods -n chorus-agent-predictor
```

**Features:**
- Horizontal Pod Autoscaling (HPA).
- Persistent Redis Storage.
- Health Probes (Liveness/Readiness).

### 3. Native Linux Deployment (Legacy/Manual)

For running directly on a VM/Metal without Docker.

```bash
# 1. Run Deployment Script
sudo ./deploy.sh deploy

# 2. Manage Service
sudo systemctl start chorus-agent-predictor
sudo systemctl status chorus-agent-predictor
```

---

## 🏥 System Management

### Health Checks

```bash
# API Health
curl http://localhost:8000/api/v1/system/health

# Scripted Check
./validate-deployment.sh

# Docker Health
./deploy-docker.sh health
```

### Logging

**Log Levels**: Configure `LOG_LEVEL` in `.env` (DEBUG, INFO, WARNING, ERROR).

**Access Logs:**
- Docker: `docker-compose logs -f`
- Systemd: `journalctl -u chorus-agent-predictor -f`

### Backup & Recovery

- **Configuration**: Backup `.env` files securely.
- **Redis Data**: Periodic RDB snapshots (`/var/lib/redis/dump.rdb`).
- **Recovery**: Services are configured to auto-restart on failure (`Restart=always`).

---

## 🔒 Security Best Practices

1.  **API Keys**: Never commit `.env` files. Use secrets management in production.
2.  **Network**: In production, ensure Redis is not exposed to the public internet. Use a firewall.
3.  **HTTPS**: Always use HTTPS for the Dashboard and API in production (handled by Nginx/Ingress).
4.  **Least Privilege**: Run services as non-root users (default in Dockerfile).

## 🛑 Uninstallation

```bash
# Docker
./deploy-docker.sh cleanup

# Native
sudo ./deploy.sh uninstall
```
