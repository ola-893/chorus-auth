# Chorus Agent Conflict Predictor Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV ENVIRONMENT=production

# Create app user
RUN groupadd -r chorus && useradd -r -g chorus chorus

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY start_system.py .
COPY .env.example .env

# Create logs directory
RUN mkdir -p logs && chown -R chorus:chorus logs

# Switch to app user
USER chorus

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "from src.system_lifecycle import lifecycle_manager; exit(0 if lifecycle_manager.is_healthy() else 1)"

# Expose port (if running API mode)
EXPOSE 8000

# Default command
CMD ["python", "start_system.py", "simulation"]