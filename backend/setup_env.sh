#!/bin/bash
# Setup script for the Chorus Agent Conflict Predictor development environment

set -e

echo "Setting up Python virtual environment for Chorus Agent Conflict Predictor..."

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Install the package in development mode
pip install -e .

echo "Environment setup complete!"
echo "To activate the environment, run: source venv/bin/activate"
echo "To run tests, use: pytest"
echo "To check code coverage, use: pytest --cov=src"