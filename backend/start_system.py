#!/usr/bin/env python3
"""
Startup script for the Chorus Agent Conflict Predictor.
This script provides a convenient way to start the system with proper error handling.
"""
import os
import sys
import subprocess
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.main import main

if __name__ == "__main__":
    # Set default environment if not specified
    if "ENVIRONMENT" not in os.environ:
        os.environ["ENVIRONMENT"] = "development"
    
    # Run the main application
    exit_code = main()
    sys.exit(exit_code)