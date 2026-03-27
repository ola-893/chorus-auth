#!/bin/bash
# Start the backend API server for the frontend to connect to
cd backend
source venv/bin/activate
export SEED_DEMO=${SEED_DEMO:-true}
export SEED_ON_STARTUP=${SEED_ON_STARTUP:-true}
uvicorn src.control_plane_app:create_app --host 0.0.0.0 --port 8000 --reload --factory
