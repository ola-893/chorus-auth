#!/bin/bash
set -e

echo "Starting Chorus Deployment..."

# 1. Start Infrastructure
echo "Starting Docker containers..."
cd backend
docker-compose up -d --build

# 2. Setup Observability
echo "Setting up Datadog Monitors..."
if [ -z "$DATADOG_API_KEY" ]; then
    echo "Skipping Datadog setup (API key missing)"
else
    python3 ../infrastructure/datadog/setup_monitors.py
fi

# 3. Build Frontend
echo "Building Frontend..."
cd ../frontend
npm install
npm run build

echo "Deployment Complete!"
