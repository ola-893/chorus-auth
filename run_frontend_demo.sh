#!/bin/bash

# Kill any existing processes on exit
trap 'kill $(jobs -p)' EXIT

echo "🎭 Starting Chorus Frontend Demo..."

# Check prerequisites
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "❌ npm not found"
    exit 1
fi

# 1. Start Backend with Simulation
echo "🚀 Launching Backend Simulation Engine..."
source venv/bin/activate || echo "⚠️  Could not activate venv, trying system python"
export PYTHONPATH=$PYTHONPATH:$(pwd)
python3 backend/frontend_demo.py &
BACKEND_PID=$!

echo "Waiting for backend to initialize..."
sleep 5

# 2. Start Frontend
echo "🎨 Starting React Dashboard..."
cd frontend
# Install dependencies if node_modules missing
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

echo "Opening dashboard..."
# Use BROWSER=none to prevent auto-open if preferred, but for demo we want it open
npm start &
FRONTEND_PID=$!

echo "✅ Demo is running!"
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo "Press Ctrl+C to stop everything."

wait
