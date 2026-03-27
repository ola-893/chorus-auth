#!/bin/bash
# Run the Chorus Comprehensive Demo with necessary environment flags

# Set default audience
AUDIENCE=${1:-technical}

echo "Starting Chorus Comprehensive Demo..."
echo "Target Audience: $AUDIENCE"
echo "Enabling Kafka, ElevenLabs, and Datadog integrations..."

# Activate virtual environment if not already active
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Set environment variables for the demo
export CHORUS_ENVIRONMENT=development
export KAFKA_ENABLED=true
export ELEVENLABS_ENABLED=true
export DATADOG_ENABLED=true
export GEMINI_MODEL="gemini-3-pro-preview"

# Check for API keys (warn if missing, but let script handle fallback/mock)
if [ -z "$ELEVENLABS_API_KEY" ]; then
    echo "WARNING: ELEVENLABS_API_KEY not set. Voice generation will be mocked or disabled."
fi
if [ -z "$GEMINI_API_KEY" ]; then
    echo "WARNING: GEMINI_API_KEY not set. Conflict prediction will be simulated."
fi

# Run the python script
python comprehensive_demo.py --audience "$AUDIENCE"
