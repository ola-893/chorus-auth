#!/bin/bash

# Chorus Multi-Agent Immune System - Demo Scenarios
# This script provides easy access to different demonstration modes

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check Python
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        print_success "Python 3 found: $PYTHON_VERSION"
    else
        print_error "Python 3 not found. Please install Python 3.9 or higher."
        exit 1
    fi
    
    # Check Redis
    if command -v redis-server &> /dev/null; then
        print_success "Redis server found"
        
        # Check if Redis is running
        if redis-cli ping &> /dev/null; then
            print_success "Redis is running"
        else
            print_warning "Redis is not running. Starting Redis..."
            redis-server --daemonize yes
            sleep 2
            if redis-cli ping &> /dev/null; then
                print_success "Redis started successfully"
            else
                print_error "Failed to start Redis"
                exit 1
            fi
        fi
    else
        print_warning "Redis not found. Some features may not work."
    fi
    
    # Check environment file
    if [ -f "backend/.env" ]; then
        print_success "Environment configuration found"
    else
        print_warning "Environment file not found. Copying from example..."
        cp backend/.env.example backend/.env
        print_info "Please edit backend/.env with your API keys"
    fi
    
    # Check virtual environment
    if [ -d "backend/venv" ]; then
        print_success "Virtual environment found"
    else
        print_info "Creating virtual environment..."
        cd backend
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
        cd ..
        print_success "Virtual environment created"
    fi
    
    echo ""
}

# Install dependencies
install_dependencies() {
    print_header "Installing Dependencies"
    
    cd backend
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install Python dependencies
    print_info "Installing Python dependencies..."
    pip install -r requirements.txt
    
    cd ..
    
    # Install frontend dependencies if needed
    if [ -d "frontend" ]; then
        print_info "Installing frontend dependencies..."
        cd frontend
        npm install
        cd ..
    fi
    
    print_success "Dependencies installed"
    echo ""
}

# Run system health check
health_check() {
    print_header "System Health Check"
    
    cd backend
    source venv/bin/activate
    
    print_info "Running system health check..."
    python -c "
import sys
sys.path.insert(0, 'src')
from system_health import SystemHealthChecker
import asyncio

async def check():
    checker = SystemHealthChecker()
    status = await checker.check_all_components()
    
    print('Component Status:')
    for component, info in status.items():
        icon = '✅' if info['healthy'] else '❌'
        print(f'  {icon} {component}: {info[\"status\"]}')
        if not info['healthy'] and 'error' in info:
            print(f'    └─ {info[\"error\"]}')

asyncio.run(check())
"
    
    cd ..
    print_success "Health check complete"
    echo ""
}

# Demo scenarios
demo_quick_start() {
    print_header "Quick Start Demo (5 minutes)"
    print_info "This demo shows basic system capabilities"
    
    cd backend
    source venv/bin/activate
    python ../comprehensive_demo.py --mode simulation --duration 300
    cd ..
}

demo_full_system() {
    print_header "Full System Demo (10 minutes)"
    print_info "Complete demonstration of all Chorus capabilities"
    
    cd backend
    source venv/bin/activate
    python ../comprehensive_demo.py --mode full --duration 600
    cd ..
}

demo_dashboard_only() {
    print_header "Dashboard Demo (3 minutes)"
    print_info "Real-time CLI dashboard demonstration"
    
    cd backend
    source venv/bin/activate
    python ../comprehensive_demo.py --mode dashboard --duration 180
    cd ..
}

demo_api_integration() {
    print_header "API Integration Demo (2 minutes)"
    print_info "REST API and external service integration"
    
    cd backend
    source venv/bin/activate
    python ../comprehensive_demo.py --mode api --duration 120
    cd ..
}

demo_conflict_prediction() {
    print_header "Conflict Prediction Demo"
    print_info "Gemini AI-powered conflict analysis"
    
    cd backend
    source venv/bin/activate
    python demo_intervention.py
    cd ..
}

demo_cli_dashboard() {
    print_header "Interactive CLI Dashboard"
    print_info "Real-time monitoring interface"
    
    cd backend
    source venv/bin/activate
    python demo_cli_dashboard.py --agents 8
    cd ..
}

# Run tests
run_tests() {
    print_header "Running Test Suite"
    
    cd backend
    source venv/bin/activate
    
    print_info "Running unit tests..."
    pytest -v -m "not integration" --tb=short
    
    print_info "Running integration tests..."
    pytest -v -m integration --tb=short
    
    print_info "Running property-based tests..."
    pytest -v -m property --tb=short
    
    cd ..
    print_success "All tests completed"
}

# Start development environment
start_dev_environment() {
    print_header "Starting Development Environment"
    
    # Start backend API
    print_info "Starting backend API server..."
    cd backend
    source venv/bin/activate
    python src/main.py &
    BACKEND_PID=$!
    cd ..
    
    # Start frontend if available
    if [ -d "frontend" ]; then
        print_info "Starting frontend development server..."
        cd frontend
        npm start &
        FRONTEND_PID=$!
        cd ..
    fi
    
    print_success "Development environment started"
    print_info "Backend API: http://localhost:8000"
    if [ -d "frontend" ]; then
        print_info "Frontend Dashboard: http://localhost:3000"
    fi
    
    print_info "Press Ctrl+C to stop all services"
    
    # Wait for interrupt
    trap 'kill $BACKEND_PID; [ ! -z "$FRONTEND_PID" ] && kill $FRONTEND_PID; exit' INT
    wait
}

# Production deployment
deploy_production() {
    print_header "Production Deployment"
    
    print_info "Running production deployment..."
    cd backend
    
    # Make deploy script executable
    chmod +x deploy.sh
    
    # Run deployment
    sudo ./deploy.sh deploy
    
    cd ..
    print_success "Production deployment complete"
}

# Docker deployment
deploy_docker() {
    print_header "Docker Deployment"
    
    print_info "Building and starting Docker containers..."
    
    # Make docker script executable
    chmod +x backend/deploy-docker.sh
    
    # Deploy with Docker
    backend/deploy-docker.sh dev
    
    print_success "Docker deployment complete"
    print_info "Backend API: http://localhost:8000"
    print_info "Frontend Dashboard: http://localhost:3000"
}

# Show menu
show_menu() {
    echo -e "${PURPLE}"
    echo "🎭 Chorus Multi-Agent Immune System - Demo Scenarios"
    echo -e "${NC}"
    echo "Choose a demonstration scenario:"
    echo ""
    echo "📋 System Management:"
    echo "  1) Check Prerequisites"
    echo "  2) Install Dependencies"
    echo "  3) System Health Check"
    echo "  4) Run Test Suite"
    echo ""
    echo "🎬 Demo Scenarios:"
    echo "  5) Quick Start Demo (5 min)"
    echo "  6) Full System Demo (10 min)"
    echo "  7) Dashboard Demo (3 min)"
    echo "  8) API Integration Demo (2 min)"
    echo "  9) Conflict Prediction Demo"
    echo " 10) Interactive CLI Dashboard"
    echo ""
    echo "🚀 Development & Deployment:"
    echo " 11) Start Development Environment"
    echo " 12) Deploy with Docker"
    echo " 13) Production Deployment"
    echo ""
    echo "  0) Exit"
    echo ""
}

# Main menu loop
main() {
    while true; do
        show_menu
        read -p "Enter your choice (0-13): " choice
        echo ""
        
        case $choice in
            1) check_prerequisites ;;
            2) install_dependencies ;;
            3) health_check ;;
            4) run_tests ;;
            5) demo_quick_start ;;
            6) demo_full_system ;;
            7) demo_dashboard_only ;;
            8) demo_api_integration ;;
            9) demo_conflict_prediction ;;
            10) demo_cli_dashboard ;;
            11) start_dev_environment ;;
            12) deploy_docker ;;
            13) deploy_production ;;
            0) 
                print_info "Goodbye!"
                exit 0
                ;;
            *)
                print_error "Invalid choice. Please try again."
                ;;
        esac
        
        echo ""
        read -p "Press Enter to continue..."
        echo ""
    done
}

# Run main menu if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi