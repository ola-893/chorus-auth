#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

# Kill any existing processes on exit
trap 'kill $(jobs -p)' EXIT

echo "Starting Chorus Auth Control Plane MVP..."

# Check prerequisites
if ! command -v python3 &> /dev/null; then
    echo "Python 3 not found"
    exit 1
fi

# 1. Start Backend
echo "Launching backend control plane..."
cd "$BACKEND_DIR"
source venv/bin/activate
export PYTHONPATH="$BACKEND_DIR"
export SEED_DEMO=${SEED_DEMO:-true}
export SEED_ON_STARTUP=${SEED_ON_STARTUP:-true}
uvicorn src.control_plane_app:create_app --host 0.0.0.0 --port 8000 --reload --factory &
BACKEND_PID=$!

echo "Waiting for backend to initialize..."
sleep 5

if [ -f "$FRONTEND_DIR/package.json" ]; then
    if ! command -v npm &> /dev/null; then
        echo "npm not found"
        exit 1
    fi

    echo "Starting frontend dashboard..."
    cd "$FRONTEND_DIR"
    if [ ! -d "node_modules" ]; then
        echo "Installing frontend dependencies..."
        npm install
    fi
    npm run dev -- --host 0.0.0.0 &
    FRONTEND_PID=$!
    echo "Frontend PID: $FRONTEND_PID"
    echo "Frontend URL: http://localhost:5173"
else
    echo "Frontend workspace is not scaffolded yet in this checkpoint. Backend remains available at http://localhost:8000."
fi

echo "Demo runtime is running."
echo "Backend PID: $BACKEND_PID"
echo "API URL: http://localhost:8000"
echo "Press Ctrl+C to stop everything."

wait
