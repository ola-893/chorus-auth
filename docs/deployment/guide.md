# Deployment Guide

This guide describes how to run the current auth control plane locally and how to move the same build toward a hosted preview.

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

Optional frontend env file:

```bash
cp .env.example .env
```

### 3. Launch the seeded demo

```bash
./run_frontend_demo.sh
```

This path starts:

- the FastAPI backend on `http://localhost:8000`
- the Vite frontend on `http://localhost:5173`
- the seeded demo workspace with the mock user, connections, agents, and scenario-ready permissions
- default local CORS origins for both Vite and common local preview ports

## Backend-Only Runtime

```bash
./run_backend_api.sh
```

This starts the control plane with the seeded defaults and exposes the REST and websocket surfaces without the frontend.

## Docker Compose

The default compose path runs the control-plane backend only.

```bash
cd backend
docker compose up --build
```

Notes:

- `SEED_ON_STARTUP=true` is enabled in the default backend service so the demo remains reproducible.

## Live Integration Mode

The repository is mock-first. To wire real auth or provider infrastructure:

1. set `AUTH_MODE=auth0`
2. populate the `AUTH0_*` variables
3. populate the `TOKEN_VAULT_*` variables
4. set `VAULT_MODE=live`
5. set `PROVIDER_MODE=live`
6. provide `GEMINI_API_KEY` if you want contextual risk enrichment

The API contracts stay the same when moving from mock adapters to live adapters.

## Hosted Preview Notes

For a hosted preview, keep the same app shape and change only runtime config:

1. set `DATABASE_URL` to a Postgres DSN such as `postgresql+psycopg://user:pass@host/dbname`
2. set `CORS_ALLOWED_ORIGINS` to the deployed frontend origin or origins
3. set `frontend/.env` so `VITE_API_BASE_URL` points to the hosted backend
4. keep `ALLOW_DEMO_MODE=true` if you want a graceful fallback path during judging
5. keep `SEED_ON_STARTUP=false` once you stop relying on automatic reseeding

Recommended hosted sequence:

- deploy backend with `/health` and `/api/meta` exposed
- deploy frontend with `VITE_API_BASE_URL` set
- verify Auth0 callback URL points at `/login/callback`
- verify connection callbacks return to `/connections`
