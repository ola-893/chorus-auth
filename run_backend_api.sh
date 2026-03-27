#!/bin/bash
# Start the backend API server for the frontend to connect to
cd backend
source venv/bin/activate
export USE_NEW_ACTION_PIPELINE=${USE_NEW_ACTION_PIPELINE:-true}
export USE_LEGACY_PIPELINE=${USE_LEGACY_PIPELINE:-false}
export SEED_DEMO=${SEED_DEMO:-true}
export SEED_ON_STARTUP=${SEED_ON_STARTUP:-true}
uvicorn src.control_plane_app:create_app --host 0.0.0.0 --port 8000 --reload --factory
