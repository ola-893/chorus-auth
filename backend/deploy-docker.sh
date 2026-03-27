#!/bin/bash
# Docker deployment script for Chorus Agent Conflict Predictor

set -e

# Configuration
APP_NAME="chorus-agent-predictor"
COMPOSE_FILE="docker-compose.yml"
PROD_COMPOSE_FILE="docker-compose.prod.yml"

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

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running. Please start Docker first."
        exit 1
    fi
}

# Setup environment
setup_environment() {
    log_info "Setting up environment"
    
    # Create .env file if it doesn't exist
    if [[ ! -f ".env" ]]; then
        if [[ -f ".env.example" ]]; then
            cp .env.example .env
            log_warn "Created .env from example. Please edit .env with your configuration"
        else
            log_error ".env.example not found. Cannot create .env file"
            exit 1
        fi
    fi
    
    # Create logs directory
    mkdir -p logs
    
    # Set proper permissions
    chmod 755 logs
}

# Build images
build_images() {
    log_info "Building Docker images"
    
    if [[ "$1" == "production" ]]; then
        docker-compose -f "$PROD_COMPOSE_FILE" build --no-cache
    else
        docker-compose -f "$COMPOSE_FILE" build --no-cache
    fi
}

# Deploy development environment
deploy_dev() {
    log_info "Deploying development environment"
    
    setup_environment
    build_images "development"
    
    # Start services
    docker-compose -f "$COMPOSE_FILE" up -d
    
    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    sleep 10
    
    # Check service status
    docker-compose -f "$COMPOSE_FILE" ps
    
    log_info "Development deployment completed!"
    log_info "Backend API: http://localhost:8000"
    log_info "Dashboard: http://localhost:3000"
    log_info "Redis: localhost:6379"
}

# Deploy production environment
deploy_prod() {
    log_info "Deploying production environment"
    
    setup_environment
    build_images "production"
    
    # Start services
    docker-compose -f "$PROD_COMPOSE_FILE" up -d
    
    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    sleep 15
    
    # Check service status
    docker-compose -f "$PROD_COMPOSE_FILE" ps
    
    log_info "Production deployment completed!"
    log_info "Application: http://localhost"
    log_info "API: http://localhost:8000"
    log_info "Redis: localhost:6379"
}

# Stop services
stop_services() {
    log_info "Stopping services"
    
    if [[ -f "$PROD_COMPOSE_FILE" ]]; then
        docker-compose -f "$PROD_COMPOSE_FILE" down
    fi
    
    if [[ -f "$COMPOSE_FILE" ]]; then
        docker-compose -f "$COMPOSE_FILE" down
    fi
    
    log_info "Services stopped"
}

# Clean up
cleanup() {
    log_info "Cleaning up Docker resources"
    
    # Stop services
    stop_services
    
    # Remove containers
    docker-compose -f "$COMPOSE_FILE" down --volumes --remove-orphans 2>/dev/null || true
    docker-compose -f "$PROD_COMPOSE_FILE" down --volumes --remove-orphans 2>/dev/null || true
    
    # Remove images
    docker images | grep "$APP_NAME" | awk '{print $3}' | xargs -r docker rmi -f
    
    # Remove unused volumes
    docker volume prune -f
    
    log_info "Cleanup completed"
}

# Show logs
show_logs() {
    local service="${1:-}"
    
    if [[ -n "$service" ]]; then
        if docker-compose -f "$PROD_COMPOSE_FILE" ps | grep -q "$service"; then
            docker-compose -f "$PROD_COMPOSE_FILE" logs -f "$service"
        elif docker-compose -f "$COMPOSE_FILE" ps | grep -q "$service"; then
            docker-compose -f "$COMPOSE_FILE" logs -f "$service"
        else
            log_error "Service '$service' not found"
            exit 1
        fi
    else
        if [[ -f "$PROD_COMPOSE_FILE" ]] && docker-compose -f "$PROD_COMPOSE_FILE" ps | grep -q "Up"; then
            docker-compose -f "$PROD_COMPOSE_FILE" logs -f
        elif [[ -f "$COMPOSE_FILE" ]] && docker-compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
            docker-compose -f "$COMPOSE_FILE" logs -f
        else
            log_error "No running services found"
            exit 1
        fi
    fi
}

# Health check
health_check() {
    log_info "Running health check"
    
    # Check backend health
    if curl -f http://localhost:8000/health &>/dev/null; then
        log_info "✓ Backend is healthy"
    else
        log_error "✗ Backend is not responding"
    fi
    
    # Check dashboard (development)
    if curl -f http://localhost:3000 &>/dev/null; then
        log_info "✓ Dashboard (dev) is healthy"
    elif curl -f http://localhost:80 &>/dev/null; then
        log_info "✓ Dashboard (prod) is healthy"
    else
        log_warn "✗ Dashboard is not responding"
    fi
    
    # Check Redis
    if docker exec -it $(docker-compose ps -q redis) redis-cli ping &>/dev/null; then
        log_info "✓ Redis is healthy"
    else
        log_error "✗ Redis is not responding"
    fi
}

# Show status
show_status() {
    log_info "Service status:"
    
    if docker-compose -f "$PROD_COMPOSE_FILE" ps 2>/dev/null | grep -q "Up"; then
        docker-compose -f "$PROD_COMPOSE_FILE" ps
    elif docker-compose -f "$COMPOSE_FILE" ps 2>/dev/null | grep -q "Up"; then
        docker-compose -f "$COMPOSE_FILE" ps
    else
        log_info "No services are running"
    fi
}

# Show usage
usage() {
    echo "Usage: $0 {dev|prod|stop|cleanup|logs|health|status}"
    echo ""
    echo "Commands:"
    echo "  dev       - Deploy development environment"
    echo "  prod      - Deploy production environment"
    echo "  stop      - Stop all services"
    echo "  cleanup   - Stop services and clean up Docker resources"
    echo "  logs      - Show logs (optionally specify service name)"
    echo "  health    - Run health check"
    echo "  status    - Show service status"
    echo ""
    echo "Examples:"
    echo "  $0 dev                    # Deploy development environment"
    echo "  $0 prod                   # Deploy production environment"
    echo "  $0 logs backend           # Show backend logs"
    echo "  $0 logs                   # Show all logs"
    exit 1
}

# Main script logic
case "${1:-}" in
    dev)
        check_docker
        deploy_dev
        ;;
    prod)
        check_docker
        deploy_prod
        ;;
    stop)
        stop_services
        ;;
    cleanup)
        cleanup
        ;;
    logs)
        show_logs "${2:-}"
        ;;
    health)
        health_check
        ;;
    status)
        show_status
        ;;
    *)
        usage
        ;;
esac