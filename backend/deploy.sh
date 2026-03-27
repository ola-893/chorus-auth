#!/bin/bash
# Deployment script for Chorus Agent Conflict Predictor

set -e

# Configuration
APP_NAME="chorus-agent-predictor"
APP_USER="chorus"
APP_DIR="/opt/chorus-agent-predictor"
SERVICE_FILE="/etc/systemd/system/chorus-agent-predictor.service"

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

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

# Create application user
create_user() {
    if ! id "$APP_USER" &>/dev/null; then
        log_info "Creating user: $APP_USER"
        useradd -r -s /bin/false -d "$APP_DIR" "$APP_USER"
    else
        log_info "User $APP_USER already exists"
    fi
}

# Install system dependencies
install_dependencies() {
    log_info "Installing system dependencies"
    
    # Update package list
    apt-get update
    
    # Install required packages
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        redis-server \
        nginx \
        nodejs \
        npm \
        curl \
        systemd \
        docker.io \
        docker-compose
    
    # Configure Redis
    cp "$APP_DIR/backend/redis.conf" /etc/redis/redis.conf
    
    # Start and enable services
    systemctl start redis-server
    systemctl enable redis-server
    systemctl start nginx
    systemctl enable nginx
    systemctl start docker
    systemctl enable docker
}

# Setup application directory
setup_app_directory() {
    log_info "Setting up application directory: $APP_DIR"
    
    # Create directory structure
    mkdir -p "$APP_DIR/backend"
    mkdir -p "$APP_DIR/backend/logs"
    mkdir -p "$APP_DIR/frontend"
    mkdir -p "$APP_DIR/infrastructure"
    
    # Copy application files
    cp -r . "$APP_DIR/backend/"
    
    # Copy frontend files if they exist
    if [[ -d "../frontend" ]]; then
        cp -r ../frontend/* "$APP_DIR/frontend/"
    fi
    
    # Copy infrastructure files if they exist
    if [[ -d "../infrastructure" ]]; then
        cp -r ../infrastructure/* "$APP_DIR/infrastructure/"
    fi
    
    # Set ownership
    chown -R "$APP_USER:$APP_USER" "$APP_DIR"
    
    # Set permissions
    chmod 755 "$APP_DIR/backend/start_system.py"
}

# Setup Python virtual environment
setup_venv() {
    log_info "Setting up Python virtual environment"
    
    cd "$APP_DIR/backend"
    
    # Create virtual environment
    sudo -u "$APP_USER" python3 -m venv venv
    
    # Install dependencies
    sudo -u "$APP_USER" venv/bin/pip install --upgrade pip
    sudo -u "$APP_USER" venv/bin/pip install -r requirements.txt
}

# Setup dashboard
setup_dashboard() {
    log_info "Setting up React dashboard"
    
    if [[ -d "$APP_DIR/frontend" ]]; then
        cd "$APP_DIR/frontend"
        
        # Install Node.js dependencies
        sudo -u "$APP_USER" npm install
        
        # Build production version
        sudo -u "$APP_USER" npm run build
        
        # Copy built files to nginx directory
        cp -r build/* /var/www/html/
        
        # Setup nginx configuration
        cp nginx.conf /etc/nginx/sites-available/chorus-dashboard
        ln -sf /etc/nginx/sites-available/chorus-dashboard /etc/nginx/sites-enabled/
        
        # Remove default nginx site
        rm -f /etc/nginx/sites-enabled/default
        
        # Test nginx configuration
        nginx -t
        
        # Reload nginx
        systemctl reload nginx
        
        log_info "Dashboard setup completed"
    else
        log_warn "Frontend directory not found, skipping dashboard setup"
    fi
}

# Setup configuration
setup_config() {
    log_info "Setting up configuration"
    
    # Copy example config if .env doesn't exist
    if [[ ! -f "$APP_DIR/backend/.env" ]]; then
        cp "$APP_DIR/backend/.env.example" "$APP_DIR/backend/.env"
        log_warn "Created .env from example. Please edit $APP_DIR/backend/.env with your configuration"
    fi
    
    # Set ownership
    chown "$APP_USER:$APP_USER" "$APP_DIR/backend/.env"
    chmod 600 "$APP_DIR/backend/.env"
}

# Install systemd service
install_service() {
    log_info "Installing systemd service"
    
    # Copy service file
    cp "$APP_DIR/backend/deployment/chorus-agent-predictor.service" "$SERVICE_FILE"
    
    # Reload systemd
    systemctl daemon-reload
    
    # Enable service
    systemctl enable chorus-agent-predictor
    
    log_info "Service installed. Use 'systemctl start chorus-agent-predictor' to start"
}

# Validate configuration
validate_config() {
    log_info "Validating configuration"
    
    cd "$APP_DIR/backend"
    
    # Run configuration validation
    if sudo -u "$APP_USER" venv/bin/python start_system.py validate-config; then
        log_info "Configuration validation passed"
    else
        log_error "Configuration validation failed. Please check your .env file"
        return 1
    fi
}

# Run health check
health_check() {
    log_info "Running health check"
    
    cd "$APP_DIR/backend"
    
    # Run health check
    if sudo -u "$APP_USER" venv/bin/python start_system.py health-check; then
        log_info "Health check passed"
    else
        log_warn "Health check failed. Some dependencies may not be available"
    fi
}

# Main deployment function
deploy() {
    log_info "Starting deployment of $APP_NAME"
    
    check_root
    create_user
    install_dependencies
    setup_app_directory
    setup_venv
    setup_dashboard
    setup_config
    install_service
    
    log_info "Deployment completed successfully!"
    log_info ""
    log_info "Next steps:"
    log_info "1. Edit configuration: $APP_DIR/backend/.env"
    log_info "2. Validate configuration: systemctl start chorus-agent-predictor"
    log_info "3. Check status: systemctl status chorus-agent-predictor"
    log_info "4. View logs: journalctl -u chorus-agent-predictor -f"
    log_info "5. Access dashboard: http://your-server-ip"
}

# Uninstall function
uninstall() {
    log_info "Uninstalling $APP_NAME"
    
    # Stop and disable service
    if systemctl is-active --quiet chorus-agent-predictor; then
        systemctl stop chorus-agent-predictor
    fi
    
    if systemctl is-enabled --quiet chorus-agent-predictor; then
        systemctl disable chorus-agent-predictor
    fi
    
    # Remove service file
    if [[ -f "$SERVICE_FILE" ]]; then
        rm "$SERVICE_FILE"
        systemctl daemon-reload
    fi
    
    # Remove application directory
    if [[ -d "$APP_DIR" ]]; then
        rm -rf "$APP_DIR"
    fi
    
    # Remove user
    if id "$APP_USER" &>/dev/null; then
        userdel "$APP_USER"
    fi
    
    log_info "Uninstall completed"
}

# Show usage
usage() {
    echo "Usage: $0 {deploy|uninstall|validate|health-check}"
    echo ""
    echo "Commands:"
    echo "  deploy      - Deploy the application"
    echo "  uninstall   - Remove the application"
    echo "  validate    - Validate configuration"
    echo "  health-check - Run health check"
    exit 1
}

# Main script logic
case "${1:-}" in
    deploy)
        deploy
        ;;
    uninstall)
        uninstall
        ;;
    validate)
        validate_config
        ;;
    health-check)
        health_check
        ;;
    *)
        usage
        ;;
esac