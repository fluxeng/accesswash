#!/bin/bash

# AccessWash Platform Startup Script
# This script starts Docker containers and Cloudflare tunnel
# Run this every time you make changes to the codebase

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
TUNNEL_ID="77255734-999d-4f75-9663-e8b10d671c16"
COMPOSE_FILE="docker-compose.yml"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${PURPLE}========================================${NC}"
    echo -e "${PURPLE}$1${NC}"
    echo -e "${PURPLE}========================================${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to wait for service to be ready
wait_for_service() {
    local service=$1
    local url=$2
    local max_attempts=30
    local attempt=1
    
    print_status "Waiting for $service to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" >/dev/null 2>&1; then
            print_success "$service is ready!"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "$service failed to start after $max_attempts attempts"
    return 1
}

# Function to check prerequisites
check_prerequisites() {
    print_header "CHECKING PREREQUISITES"
    
    # Check Docker
    if ! command_exists docker; then
        print_error "Docker is not installed!"
        exit 1
    fi
    print_success "Docker found"
    
    # Check Docker Compose
    if ! command_exists docker-compose; then
        print_error "Docker Compose is not installed!"
        exit 1
    fi
    print_success "Docker Compose found"
    
    # Check Cloudflared
    if ! command_exists cloudflared; then
        print_error "Cloudflared is not installed!"
        print_status "Install with: wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb && sudo dpkg -i cloudflared-linux-amd64.deb"
        exit 1
    fi
    print_success "Cloudflared found"
    
    # Check if we're in the right directory
    if [ ! -f "$COMPOSE_FILE" ]; then
        print_error "docker-compose.yml not found! Make sure you're in the accesswash_platform directory"
        exit 1
    fi
    print_success "Found docker-compose.yml"
    
    # Check tunnel credentials
    if [ ! -f "$HOME/.cloudflared/$TUNNEL_ID.json" ]; then
        print_error "Tunnel credentials not found!"
        print_status "Run: cloudflared tunnel login"
        exit 1
    fi
    print_success "Tunnel credentials found"
}

# Function to stop existing services
stop_services() {
    print_header "STOPPING EXISTING SERVICES"
    
    # Stop Docker containers
    print_status "Stopping Docker containers..."
    docker-compose down || true
    
    # Stop any running tunnel
    print_status "Stopping existing tunnel..."
    pkill -f "cloudflared tunnel" || true
    
    print_success "Existing services stopped"
}

# Function to start Docker services
start_docker() {
    print_header "STARTING DOCKER SERVICES"
    
    print_status "Building and starting Docker containers..."
    docker-compose up --build -d
    
    print_status "Checking container status..."
    docker-compose ps
    
    # Wait for database to be ready
    print_status "Waiting for database to initialize..."
    sleep 15
    
    # Wait for web service
    wait_for_service "Django" "http://localhost:8000/health/"
    
    print_success "Docker services started successfully"
}

# Function to run Django setup
setup_django() {
    print_header "SETTING UP DJANGO"
    
    print_status "Running database migrations..."
    docker-compose exec -T web python manage.py migrate_schemas --shared || {
        print_warning "Shared migrations failed, trying again..."
        sleep 5
        docker-compose exec -T web python manage.py migrate_schemas --shared
    }
    
    print_status "Creating demo data..."
    docker-compose exec -T web python setup_data.py || {
        print_warning "Demo data creation failed, but continuing..."
    }
    
    print_success "Django setup completed"
}

# Function to start Cloudflare tunnel
start_tunnel() {
    print_header "STARTING CLOUDFLARE TUNNEL"
    
    # Create tunnel config if it doesn't exist
    mkdir -p ~/.cloudflared
    
    if [ ! -f ~/.cloudflared/config.yml ]; then
        print_status "Creating tunnel configuration..."
        cat > ~/.cloudflared/config.yml << EOF
tunnel: $TUNNEL_ID
credentials-file: ~/.cloudflared/$TUNNEL_ID.json

ingress:
  - hostname: api.accesswash.org
    service: http://localhost:8000
  - hostname: demo.accesswash.org
    service: http://localhost:8000
  - hostname: app.accesswash.org
    service: http://localhost:8000
  - service: http_status:404
EOF
        print_success "Tunnel configuration created"
    fi
    
    # Validate tunnel config
    print_status "Validating tunnel configuration..."
    cloudflared tunnel --config ~/.cloudflared/config.yml ingress validate
    
    # Start tunnel in background
    print_status "Starting Cloudflare tunnel..."
    nohup cloudflared tunnel --config ~/.cloudflared/config.yml run > tunnel.log 2>&1 &
    
    # Save tunnel PID
    echo $! > tunnel.pid
    
    # Wait a moment for tunnel to connect
    sleep 5
    
    # Check if tunnel is running
    if ps -p $(cat tunnel.pid) > /dev/null; then
        print_success "Cloudflare tunnel started successfully (PID: $(cat tunnel.pid))"
    else
        print_error "Failed to start Cloudflare tunnel"
        print_status "Check tunnel.log for details"
        return 1
    fi
}

# Function to test the deployment
test_deployment() {
    print_header "TESTING DEPLOYMENT"
    
    # Test local endpoints
    print_status "Testing local endpoints..."
    if curl -s http://localhost:8000/health/ | grep -q "AccessWash"; then
        print_success "Local health check passed"
    else
        print_error "Local health check failed"
    fi
    
    # Test live endpoints (wait a bit for tunnel to propagate)
    print_status "Waiting for tunnel to propagate..."
    sleep 10
    
    print_status "Testing live endpoints..."
    
    # Test API endpoint
    if curl -s https://api.accesswash.org/health/ | grep -q "AccessWash"; then
        print_success "API endpoint working"
    else
        print_warning "API endpoint not responding yet (DNS propagation?)"
    fi
    
    # Test demo endpoint
    if curl -s https://demo.accesswash.org/health/ | grep -q "AccessWash"; then
        print_success "Demo endpoint working"
    else
        print_warning "Demo endpoint not responding yet (DNS propagation?)"
    fi
}

# Function to show status and URLs
show_status() {
    print_header "ACCESSWASH PLATFORM STATUS"
    
    echo -e "${GREEN}🎉 AccessWash Platform is running!${NC}"
    echo ""
    echo -e "${BLUE}📊 Docker Containers:${NC}"
    docker-compose ps
    echo ""
    echo -e "${BLUE}🌐 Live URLs:${NC}"
    echo -e "  🏢 Platform Admin:  ${GREEN}https://api.accesswash.org/admin/${NC}"
    echo -e "  🚰 Demo Utility:    ${GREEN}https://demo.accesswash.org/admin/${NC}"
    echo -e "  📚 API Docs:        ${GREEN}https://demo.accesswash.org/api/docs/${NC}"
    echo -e "  ❤️  Health Check:    ${GREEN}https://demo.accesswash.org/health/${NC}"
    echo ""
    echo -e "${BLUE}🔐 Login Credentials:${NC}"
    echo -e "  Platform: ${YELLOW}kkimtai@gmail.com${NC} / ${YELLOW}Aspire2infinity${NC}"
    echo -e "  Demo Manager: ${YELLOW}manager@nairobidemo.accesswash.org${NC} / ${YELLOW}Aspire2infinity${NC}"
    echo -e "  Field Tech: ${YELLOW}field1@nairobidemo.accesswash.org${NC} / ${YELLOW}Aspire2infinity${NC}"
    echo ""
    echo -e "${BLUE}📝 Logs:${NC}"
    echo -e "  Docker: ${YELLOW}docker-compose logs -f web${NC}"
    echo -e "  Tunnel: ${YELLOW}tail -f tunnel.log${NC}"
    echo ""
    echo -e "${BLUE}🛑 Stop Services:${NC}"
    echo -e "  ${YELLOW}./stop_accesswash.sh${NC} or ${YELLOW}docker-compose down && pkill -f cloudflared${NC}"
}

# Function to handle cleanup on exit
cleanup() {
    if [ -f tunnel.pid ]; then
        print_status "Cleaning up tunnel process..."
        kill $(cat tunnel.pid) 2>/dev/null || true
        rm -f tunnel.pid
    fi
}

# Set trap for cleanup
trap cleanup EXIT

# Main execution
main() {
    print_header "ACCESSWASH PLATFORM STARTUP"
    echo -e "${GREEN}Starting AccessWash Platform with live deployment...${NC}"
    echo ""
    
    # Run all steps
    check_prerequisites
    stop_services
    start_docker
    setup_django
    start_tunnel
    test_deployment
    show_status
    
    print_success "AccessWash Platform startup completed!"
    
    # Keep tunnel running in foreground
    print_status "Tunnel is running in background. Press Ctrl+C to stop all services."
    
    # Wait for tunnel process or user interrupt
    if [ -f tunnel.pid ]; then
        while ps -p $(cat tunnel.pid) > /dev/null; do
            sleep 5
        done
        print_error "Tunnel process died unexpectedly"
    fi
}

# Run main function
main "$@"