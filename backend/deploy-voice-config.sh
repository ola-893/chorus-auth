#!/bin/bash
# Deployment configuration for Voice Alert Service

# 1. Environment Setup
echo "Configuring Voice Alert Service..."

# Ensure required environment variables
if [ -z "$ELEVENLABS_API_KEY" ]; then
    echo "WARNING: ELEVENLABS_API_KEY not set. Voice generation will be disabled."
fi

# Set default voice profile if not set
export ELEVENLABS_VOICE_ID=${ELEVENLABS_VOICE_ID:-"21m00Tcm4TlvDq8ikWAM"} # Rachel

# 2. Audio Storage Configuration
# Create persistent storage directory for audio files
AUDIO_STORAGE_DIR=${AUDIO_STORAGE_PATH:-"./backend/alerts"}
mkdir -p "$AUDIO_STORAGE_DIR"
echo "Audio storage configured at: $AUDIO_STORAGE_DIR"

# 3. Cleanup Policy Configuration
# Setup cron job for audio cleanup (older than 24h)
# This assumes a standard linux environment
CRON_JOB="0 * * * * python3 $(pwd)/backend/src/scripts/cleanup_audio.py --days 1 --dir $AUDIO_STORAGE_DIR"

# Check if cron job exists, if not add it (idempotent-ish check)
# crontab -l | grep -q "cleanup_audio.py"
# if [ $? -ne 0 ]; then
#    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
#    echo "Cleanup cron job installed."
# else
#    echo "Cleanup cron job already exists."
# fi

echo "Voice Alert Service configuration complete."
