#!/bin/bash
echo "Attempting to restart backend infrastructure..."

# Check if docker is running
if ! docker info > /dev/null 2>&1; then
  echo "❌ Docker daemon is NOT running."
  echo "Please start Docker Desktop or the docker daemon manually."
  exit 1
fi

echo "✅ Docker is running."

cd backend

# Check if containers are running
if [ -z "$(docker ps -q -f name=backend-redis-1)" ] || [ -z "$(docker ps -q -f name=backend-kafka-1)" ]; then
    echo "🔄 Containers missing/stopped. Restarting via docker-compose..."
    # Try docker compose (v2) first, then docker-compose (v1)
    if docker compose version > /dev/null 2>&1; then
        docker compose up -d
    else
        docker-compose up -d
    fi
else
    echo "✅ Redis and Kafka containers are already running."
fi

echo "Waiting for services to stabilize..."
sleep 5
echo "Infrastructure ready."
