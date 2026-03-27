#!/bin/bash
# Deployment validation script for Chorus Agent Conflict Predictor

set -e

# Configuration
BACKEND_URL="http://localhost:8000"
DASHBOARD_URL="http://localhost:3000"
REDIS_HOST="localhost"
REDIS_PORT="6379"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check if a service is running on a port
check_port() {
    local port=$1
    local service_name=$2
    
    if nc -z localhost "$port" 2>/dev/null; then
        log_success "$service_name is running on port $port"
        return 0
    else
        log_error "$service_name is not running on port $port"
        return 1
    fi
}

# Check HTTP endpoint
check_http_endpoint() {
    local url=$1
    local service_name=$2
    local timeout=${3:-10}
    
    if curl -f -s --max-time "$timeout" "$url" > /dev/null; then
        log_success "$service_name is responding at $url"
        return 0
    else
        log_error "$service_name is not responding at $url"
        return 1
    fi
}

# Check Redis connectivity
check_redis() {
    log_info "Checking Redis connectivity..."
    
    if command -v redis-cli &> /dev/null; then
        if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping | grep -q "PONG"; then
            log_success "Redis is responding"
            
            # Check Redis info
            local redis_info=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" info server | grep redis_version)
            log_info "Redis version: $redis_info"
            
            return 0
        else
            log_error "Redis is not responding"
            return 1
        fi
    else
        log_warn "redis-cli not found, skipping Redis connectivity check"
        return 1
    fi
}

# Check backend API
check_backend_api() {
    log_info "Checking backend API..."
    
    # Check if backend is running
    if ! check_port 8000 "Backend API"; then
        return 1
    fi
    
    # Check health endpoint
    if check_http_endpoint "$BACKEND_URL/health" "Backend health endpoint"; then
        # Get health status
        local health_response=$(curl -s "$BACKEND_URL/health" 2>/dev/null)
        log_info "Health status: $health_response"
    fi
    
    # Check API endpoints
    check_http_endpoint "$BACKEND_URL/api/v1/agents" "Agents API endpoint" || true
    check_http_endpoint "$BACKEND_URL/api/v1/system/health" "System health API endpoint" || true
    
    return 0
}

# Check dashboard
check_dashboard() {
    log_info "Checking React dashboard..."
    
    # Check if dashboard is running (development)
    if check_port 3000 "Dashboard (development)"; then
        check_http_endpoint "$DASHBOARD_URL" "Dashboard homepage"
        return 0
    fi
    
    # Check if dashboard is running (production)
    if check_port 80 "Dashboard (production)"; then
        check_http_endpoint "http://localhost" "Dashboard homepage (production)"
        return 0
    fi
    
    log_warn "Dashboard is not running on expected ports (3000 or 80)"
    return 1
}

# Check configuration
check_configuration() {
    log_info "Checking configuration..."
    
    # Check if .env file exists
    if [[ -f ".env" ]]; then
        log_success ".env file exists"
        
        # Check required environment variables
        local required_vars=("CHORUS_GEMINI_API_KEY" "CHORUS_REDIS_HOST" "CHORUS_REDIS_PORT")
        local missing_vars=()
        
        for var in "${required_vars[@]}"; do
            if ! grep -q "^$var=" .env; then
                missing_vars+=("$var")
            fi
        done
        
        if [[ ${#missing_vars[@]} -eq 0 ]]; then
            log_success "All required environment variables are present"
        else
            log_error "Missing required environment variables: ${missing_vars[*]}"
            return 1
        fi
    else
        log_error ".env file not found"
        return 1
    fi
    
    return 0
}

# Check Docker services
check_docker_services() {
    log_info "Checking Docker services..."
    
    if command -v docker-compose &> /dev/null; then
        # Check if services are running
        local running_services=$(docker-compose ps --services --filter "status=running" 2>/dev/null)
        
        if [[ -n "$running_services" ]]; then
            log_success "Docker services are running:"
            echo "$running_services" | while read -r service; do
                log_info "  - $service"
            done
        else
            log_warn "No Docker services are running"
        fi
    else
        log_warn "docker-compose not found, skipping Docker services check"
    fi
}

# Check system resources
check_system_resources() {
    log_info "Checking system resources..."
    
    # Check available memory
    local available_memory=$(free -m | awk 'NR==2{printf "%.1f", $7/1024}')
    log_info "Available memory: ${available_memory}GB"
    
    # Check disk space
    local disk_usage=$(df -h . | awk 'NR==2{print $5}' | sed 's/%//')
    log_info "Disk usage: ${disk_usage}%"
    
    if [[ $disk_usage -gt 90 ]]; then
        log_warn "Disk usage is high (${disk_usage}%)"
    fi
    
    # Check CPU load
    local cpu_load=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
    log_info "CPU load average: $cpu_load"
}

# Check log files
check_logs() {
    log_info "Checking log files..."
    
    # Check for recent errors in logs
    local log_files=("logs/chorus.log" "/var/log/chorus/chorus.log")
    
    for log_file in "${log_files[@]}"; do
        if [[ -f "$log_file" ]]; then
            log_info "Found log file: $log_file"
            
            # Check for recent errors
            local recent_errors=$(tail -100 "$log_file" | grep -i error | wc -l)
            if [[ $recent_errors -gt 0 ]]; then
                log_warn "Found $recent_errors recent errors in $log_file"
            else
                log_success "No recent errors in $log_file"
            fi
        fi
    done
}

# Run comprehensive validation
run_validation() {
    log_info "Starting deployment validation..."
    echo
    
    local checks_passed=0
    local total_checks=0
    
    # Configuration check
    ((total_checks++))
    if check_configuration; then
        ((checks_passed++))
    fi
    echo
    
    # Redis check
    ((total_checks++))
    if check_redis; then
        ((checks_passed++))
    fi
    echo
    
    # Backend API check
    ((total_checks++))
    if check_backend_api; then
        ((checks_passed++))
    fi
    echo
    
    # Dashboard check
    ((total_checks++))
    if check_dashboard; then
        ((checks_passed++))
    fi
    echo
    
    # Docker services check
    check_docker_services
    echo
    
    # System resources check
    check_system_resources
    echo
    
    # Log files check
    check_logs
    echo
    
    # Summary
    log_info "Validation Summary:"
    log_info "Checks passed: $checks_passed/$total_checks"
    
    if [[ $checks_passed -eq $total_checks ]]; then
        log_success "All critical checks passed! Deployment appears to be healthy."
        return 0
    else
        log_error "Some checks failed. Please review the issues above."
        return 1
    fi
}

# Show usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --backend-url URL     Backend API URL (default: $BACKEND_URL)"
    echo "  --dashboard-url URL   Dashboard URL (default: $DASHBOARD_URL)"
    echo "  --redis-host HOST     Redis host (default: $REDIS_HOST)"
    echo "  --redis-port PORT     Redis port (default: $REDIS_PORT)"
    echo "  --help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Run with default settings"
    echo "  $0 --backend-url http://api.example.com"
    echo "  $0 --redis-host redis.example.com --redis-port 6380"
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --backend-url)
            BACKEND_URL="$2"
            shift 2
            ;;
        --dashboard-url)
            DASHBOARD_URL="$2"
            shift 2
            ;;
        --redis-host)
            REDIS_HOST="$2"
            shift 2
            ;;
        --redis-port)
            REDIS_PORT="$2"
            shift 2
            ;;
        --help)
            usage
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            ;;
    esac
done

# Main execution
if command -v nc &> /dev/null; then
    run_validation
else
    log_error "netcat (nc) is required for port checking. Please install it first."
    exit 1
fi