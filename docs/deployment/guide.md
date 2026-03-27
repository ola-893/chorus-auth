# Deployment Guide

This guide describes how to run the current auth control plane MVP locally.

## Recommended Local Path

### 1. Backend setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Frontend setup

```bash
cd frontend
npm install
```

### 3. Launch the seeded demo

```bash
./run_frontend_demo.sh
```

This path starts:

- the FastAPI backend on `http://localhost:8000`
- the Vite frontend on `http://localhost:5173`
- the seeded demo workspace with the mock user, connections, agents, and scenario-ready permissions

## Backend-Only Runtime

```bash
./run_backend_api.sh
```

This starts the control plane with the seeded defaults and exposes the REST and websocket surfaces without the frontend.

## Docker Compose

The default compose path runs Redis and the control-plane backend only.

```bash
cd backend
docker compose up --build
```

Notes:

- `SEED_ON_STARTUP=true` is enabled in the default backend service so the demo remains reproducible.
- Kafka and Zookeeper remain available only behind the `legacy` profile for historical experiments.

## Live Integration Mode

The repository is mock-first. To wire real auth or provider infrastructure:

1. set `AUTH_MODE=auth0`
2. populate the `AUTH0_*` variables
3. populate the `TOKEN_VAULT_*` variables
4. provide `GEMINI_API_KEY` if you want contextual risk enrichment

The API contracts stay the same when moving from mock adapters to live adapters.
