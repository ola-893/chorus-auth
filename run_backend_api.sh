#!/bin/bash
# Start the backend API server for the frontend to connect to
source venv/bin/activate
cd backend
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
