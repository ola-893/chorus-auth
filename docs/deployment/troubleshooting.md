# Deployment Troubleshooting Guide

This guide helps diagnose and resolve common deployment issues with the Chorus Agent Conflict Predictor system.

## Quick Diagnostic Commands

Run these commands first to get an overview of system status:

```bash
# Comprehensive deployment validation
./validate-deployment.sh

# System health check
python start_system.py health-check

# Configuration validation
python start_system.py validate-config

# System status
python -c "from src.system_lifecycle import get_system_status; print(get_system_status())"
```

## Common Issues and Solutions

### 1. Configuration Issues

#### Problem: "Gemini API key is required"
```
ConfigurationError: Gemini API key is required
```

**Solution:**
```bash
# Check if API key is set
echo $CHORUS_GEMINI_API_KEY

# Set API key in .env file
echo "CHORUS_GEMINI_API_KEY=your_actual_api_key_here" >> .env
```

#### Problem: "Redis connection failed"
```
ConnectionError: Redis connection failed
```

**Solution:**
```bash
# Check Redis server status
redis-cli ping

# Check Redis configuration
redis-cli info server

# Test connection with specific host/port
redis-cli -h $CHORUS_REDIS_HOST -p $CHORUS_REDIS_PORT ping
```

### 2. Dependency Issues

#### Problem: "Required dependencies failed"
```
DependencyError: Required dependencies failed: ['redis_connection', 'gemini_api']
```

**Solution:**
Run dependency checks manually:
```bash
python -c "
from src.system_lifecycle import lifecycle_manager
for name, check in lifecycle_manager.dependency_checks.items():
    try:
        result = check.check_function()
        print(f'{name}: {'PASS' if result else 'FAIL'}')
    except Exception as e:
        print(f'{name}: ERROR - {e}')
"
```

### 3. Docker Issues

#### Problem: "Docker services not starting"
```bash
# Check Docker daemon status
sudo systemctl status docker

# Check Docker Compose logs
./deploy-docker.sh logs

# Restart Docker services
./deploy-docker.sh stop
./deploy-docker.sh dev  # or prod
```

#### Problem: "Port already in use"
```
Error: Port 8000 is already in use
```

**Solution:**
```bash
# Find process using the port
sudo lsof -i :8000

# Kill process if safe to do so
sudo kill -9 <PID>

# Or change port in configuration (.env)
CHORUS_API_PORT=8001
```

### 4. Database Issues

#### Problem: "Redis memory issues"
```
Redis OOM: Out of memory
```

**Solution:**
```bash
# Check Redis memory usage
redis-cli info memory

# Configure maxmemory (if needed)
redis-cli config set maxmemory 256mb
redis-cli config set maxmemory-policy allkeys-lru
```

### 5. Performance Issues

#### Problem: "High CPU usage"
Check if agent count is too high for the host resources:
```bash
# Check agent count settings
grep "AGENTS" .env

# Reduce agent count temporarily
echo "CHORUS_MAX_AGENTS=5" >> .env
```

## Diagnostic Scripts

### System Health Check Script
```bash
#!/bin/bash
# save as health_check.sh

echo "=== Chorus System Health Check ==="

# Configuration
echo "1. Configuration Check:"
python start_system.py validate-config

# Dependencies
echo "2. Dependency Check:"
python start_system.py health-check

# Services
echo "3. Service Check:"
curl -f http://localhost:8000/health && echo "API: OK" || echo "API: FAIL"
redis-cli ping && echo "Redis: OK" || echo "Redis: FAIL"

# Resources
echo "4. Resource Check:"
free -h
df -h .
```

## Getting Help

### Log Collection for Support
```bash
# Collect system information
./validate-deployment.sh > system_info.txt 2>&1

# Collect recent logs
tail -500 logs/chorus.log > recent_logs.txt

# Create support bundle
tar -czf chorus_support_$(date +%Y%m%d).tar.gz system_info.txt recent_logs.txt
```

### Debug Mode
```bash
# Enable debug mode
export CHORUS_DEBUG=true
export CHORUS_LOG_LEVEL=DEBUG

# Run with debug output
python start_system.py simulation
```
