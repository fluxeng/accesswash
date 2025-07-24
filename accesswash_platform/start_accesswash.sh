#!/bin/bash

# File: accesswash_platform/start_accesswash.sh
# Enhanced AccessWash Platform Startup Script with better error handling

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
TUNNEL_ID="${TUNNEL_ID:-5420642c-7326-407f-9fdc-0ec4285818c0}"
LOG_FILE="accesswash.log"
MAX_RETRIES=3

# Command-line flags
FORCE_DB_SETUP=false
SKIP_TUNNEL=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --force-db-setup)
            FORCE_DB_SETUP=true
            shift
            ;;
        --skip-tunnel)
            SKIP_TUNNEL=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Logging functions
log() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}✓${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}✗${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1" | tee -a "$LOG_FILE"
}

header() {
    echo -e "${YELLOW}========== $1 ==========${NC}" | tee -a "$LOG_FILE"
}

# Enhanced command runner with retries
run_cmd_with_retry() {
    local cmd="$1"
    local max_attempts="${2:-$MAX_RETRIES}"
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        log "Attempt $attempt/$max_attempts: $cmd"
        if eval "$cmd" 2>&1 | tee -a "$LOG_FILE"; then
            return 0
        else
            if [ $attempt -eq $max_attempts ]; then
                error "Command failed after $max_attempts attempts: $cmd"
                return 1
            fi
            warning "Attempt $attempt failed, retrying in 5 seconds..."
            sleep 5
            ((attempt++))
        fi
    done
}

# Initialize log
echo "AccessWash Platform Startup - $(date)" > "$LOG_FILE"

# Check prerequisites
check_prerequisites() {
    header "CHECKING PREREQUISITES"
    
    local all_good=true
    
    # Check Docker
    if ! command -v docker >/dev/null 2>&1; then
        error "Docker not installed"
        all_good=false
    else
        success "Docker found: $(docker --version | cut -d' ' -f3)"
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose >/dev/null 2>&1; then
        error "Docker Compose not installed"
        all_good=false
    else
        success "Docker Compose found: $(docker-compose --version | cut -d' ' -f3)"
    fi
    
    # Check Cloudflared (only if not skipping tunnel)
    if [ "$SKIP_TUNNEL" = false ]; then
        if ! command -v cloudflared >/dev/null 2>&1; then
            error "Cloudflared not installed"
            all_good=false
        else
            success "Cloudflared found: $(cloudflared --version 2>&1 | head -1)"
        fi
        
        # Check tunnel credentials
        if [ ! -f "$HOME/.cloudflared/$TUNNEL_ID.json" ]; then
            error "Tunnel credentials not found at $HOME/.cloudflared/$TUNNEL_ID.json"
            all_good=false
        else
            success "Tunnel credentials found"
        fi
    fi
    
    # Check required files
    local required_files=("docker-compose.yml" "manage.py" "requirements.txt")
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            error "Required file not found: $file"
            all_good=false
        else
            success "Found: $file"
        fi
    done
    
    if [ "$all_good" = false ]; then
        error "Prerequisites check failed"
        exit 1
    fi
    
    success "All prerequisites satisfied"
}

# Enhanced cleanup
cleanup_services() {
    header "CLEANING UP EXISTING SERVICES"
    
    # Stop existing processes
    if [ -f "tunnel.pid" ]; then
        local tunnel_pid=$(cat tunnel.pid 2>/dev/null)
        if [ -n "$tunnel_pid" ] && ps -p "$tunnel_pid" >/dev/null 2>&1; then
            log "Stopping tunnel process (PID: $tunnel_pid)"
            kill "$tunnel_pid" 2>/dev/null || true
        fi
        rm -f tunnel.pid
    fi
    
    if [ -f "docker_logs.pid" ]; then
        local log_pid=$(cat docker_logs.pid 2>/dev/null)
        if [ -n "$log_pid" ] && ps -p "$log_pid" >/dev/null 2>&1; then
            log "Stopping log monitoring (PID: $log_pid)"
            kill "$log_pid" 2>/dev/null || true
        fi
        rm -f docker_logs.pid
    fi
    
    # Kill cloudflared processes
    pkill -f "cloudflared tunnel" 2>/dev/null || true
    
    # Clean up ports
    for port in 5432 6379 8000; do
        if lsof -ti:$port >/dev/null 2>&1; then
            log "Killing processes on port $port"
            lsof -ti:$port | xargs kill -9 2>/dev/null || true
        fi
    done
    
    # Stop Docker containers
    log "Stopping Docker containers..."
    docker-compose down --timeout 30 --remove-orphans 2>/dev/null || true
    
    success "Cleanup completed"
}

# Enhanced Docker startup
start_docker() {
    header "STARTING DOCKER SERVICES"
    
    log "Building and starting containers..."
    if ! run_cmd_with_retry "docker-compose up --build -d"; then
        error "Failed to start Docker containers"
        show_docker_logs
        exit 1
    fi
    
    # Wait for database with better checking
    log "Waiting for database..."
    local db_attempts=0
    local max_db_attempts=60
    
    while [ $db_attempts -lt $max_db_attempts ]; do
        if docker-compose exec -T db pg_isready -U accesswash_user -d accesswash_db >/dev/null 2>&1; then
            success "Database ready"
            break
        fi
        echo -n "."
        sleep 2
        ((db_attempts++))
    done
    
    if [ $db_attempts -eq $max_db_attempts ]; then
        error "Database failed to start within $(($max_db_attempts * 2)) seconds"
        show_docker_logs
        exit 1
    fi
    
    # Wait for Django with multiple checks
    log "Waiting for Django application..."
    local django_attempts=0
    local max_django_attempts=45
    
    while [ $django_attempts -lt $max_django_attempts ]; do
        # Try multiple health check methods
        if docker-compose exec -T web python manage.py check >/dev/null 2>&1; then
            success "Django management commands ready"
            break
        elif curl -s http://localhost:8000/health/ >/dev/null 2>&1; then
            success "Django web server responding"
            break
        elif curl -s http://localhost:8000/ping/ >/dev/null 2>&1; then
            success "Django basic health check responding"
            break
        fi
        echo -n "."
        sleep 3
        ((django_attempts++))
    done
    
    if [ $django_attempts -eq $max_django_attempts ]; then
        error "Django failed to start within $(($max_django_attempts * 3)) seconds"
        show_docker_logs
        exit 1
    fi
    
    success "Docker services started successfully"
}

# Show Docker logs for debugging
show_docker_logs() {
    log "=== RECENT DOCKER LOGS ==="
    docker-compose logs --tail=20 2>/dev/null || true
}

# Database existence check
database_exists() {
    if docker-compose exec -T db psql -U accesswash_user -d accesswash_db -tAc \
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'django_migrations')" 2>/dev/null | grep -q "t"; then
        return 0
    else
        return 1
    fi
}

# Enhanced Django setup
setup_django() {
    header "DJANGO APPLICATION SETUP"
    
    if [ "$FORCE_DB_SETUP" = false ] && database_exists; then
        success "Database already exists - skipping setup"
        return 0
    fi
    
    log "Running Django migrations..."
    if ! run_cmd_with_retry "docker-compose exec -T web python manage.py migrate" 2; then
        log "Standard migrate failed, trying tenant schemas..."
        if ! run_cmd_with_retry "docker-compose exec -T web python manage.py migrate_schemas --shared" 2; then
            error "All migration attempts failed"
            show_docker_logs
            exit 1
        fi
    fi
    
    log "Collecting static files..."
    run_cmd_with_retry "docker-compose exec -T web python manage.py collectstatic --noinput" 1 || warning "Static file collection failed"
    
    log "Creating demo data..."
    if run_cmd_with_retry "docker-compose exec -T web python setup_data.py" 2; then
        success "Demo data created successfully"
    else
        warning "Demo data creation failed - continuing anyway"
    fi
    
    success "Django setup completed"
}

# Enhanced tunnel startup
start_tunnel() {
    if [ "$SKIP_TUNNEL" = true ]; then
        warning "Skipping tunnel startup as requested"
        return 0
    fi
    
    header "STARTING CLOUDFLARE TUNNEL"
    
    # Create/update tunnel config
    log "Updating tunnel configuration..."
    mkdir -p ~/.cloudflared
    
    cat > ~/.cloudflared/config.yml << 'EOF'
tunnel: 5420642c-7326-407f-9fdc-0ec4285818c0
credentials-file: ~/..cloudflared/5420642c-7326-407f-9fdc-0ec4285818c0.json

ingress:
  - hostname: health.accesswash.org
    service: http://localhost:8000/health/
    
  - hostname: api.accesswash.org
    service: http://localhost:8000
    originRequest:
      httpHostHeader: api.accesswash.org
      
  - hostname: demo.accesswash.org
    service: http://localhost:8000
    originRequest:
      httpHostHeader: demo.accesswash.org
      
  - hostname: app.accesswash.org
    service: http://localhost:8000
    originRequest:
      httpHostHeader: app.accesswash.org
      
  - hostname: "*.accesswash.org"
    service: http://localhost:8000
    originRequest:
      httpHostHeader: "*.accesswash.org"
      
  - service: http_status:404
EOF
    
    # Test tunnel configuration
    log "Testing tunnel configuration..."
    if ! cloudflared tunnel --config ~/.cloudflared/config.yml ingress validate; then
        error "Tunnel configuration validation failed"
        exit 1
    fi
    
    # Start tunnel
    log "Starting Cloudflare tunnel..."
    nohup cloudflared tunnel --config ~/.cloudflared/config.yml run >> "$LOG_FILE" 2>&1 &
    tunnel_pid=$!
    echo $tunnel_pid > tunnel.pid
    disown $tunnel_pid
    
    # Wait for tunnel to be ready
    sleep 5
    if ps -p $tunnel_pid >/dev/null; then
        success "Tunnel started successfully (PID: $tunnel_pid)"
        
        # Test tunnel connectivity
        log "Testing tunnel connectivity..."
        sleep 10
        if curl -s https://health.accesswash.org/ >/dev/null 2>&1; then
            success "Tunnel connectivity verified"
        else
            warning "Tunnel may not be fully ready yet"
        fi
    else
        error "Tunnel failed to start"
        exit 1
    fi
}

# Start log monitoring
start_logs() {
    log "Starting background log monitoring..."
    nohup docker-compose logs -f --tail=50 >> "$LOG_FILE" 2>&1 &
    docker_logs_pid=$!
    echo $docker_logs_pid > docker_logs.pid
    disown $docker_logs_pid
    success "Log monitoring started (PID: $docker_logs_pid)"
}

# Final status display
show_status() {
    header "PLATFORM STATUS"
    
    echo ""
    echo -e "${GREEN}🎉 AccessWash Platform is running!${NC}"
    echo ""
    echo -e "${BLUE}Local URLs:${NC}"
    echo "  Health:   http://localhost:8000/health/"
    echo "  Admin:    http://localhost:8000/admin/"
    echo "  API Docs: http://localhost:8000/api/docs/"
    echo ""
    
    if [ "$SKIP_TUNNEL" = false ]; then
        echo -e "${BLUE}Remote URLs:${NC}"
        echo "  Health:   https://health.accesswash.org/"
        echo "  Platform: https://api.accesswash.org/admin/"
        echo "  Demo:     https://demo.accesswash.org/admin/"
        echo "  API Docs: https://demo.accesswash.org/api/docs/"
        echo ""
    fi
    
    echo -e "${BLUE}Login Credentials:${NC}"
    echo "  Platform: kkimtai@gmail.com / Welcome1!"
    echo "  Demo:     demo1@accesswash.org / Welcome1!"
    echo ""
    echo -e "${BLUE}Management Commands:${NC}"
    echo "  Logs:     tail -f $LOG_FILE"
    echo "  Stop:     ./stop_accesswash.sh"
    echo "  Restart:  $0 --force-db-setup"
    echo "  Django:   docker-compose exec web python manage.py shell"
    echo ""
    echo -e "${BLUE}Debug Commands:${NC}"
    echo "  Web logs: docker-compose logs web"
    echo "  DB logs:  docker-compose logs db"
    echo "  All logs: docker-compose logs"
    echo ""
}

# Error cleanup handler
cleanup_on_error() {
    if [[ $? -ne 0 ]]; then
        error "Startup failed - cleaning up..."
        show_docker_logs
        docker-compose down --remove-orphans 2>/dev/null || true
        pkill -f cloudflared 2>/dev/null || true
        rm -f tunnel.pid docker_logs.pid
    fi
}

trap cleanup_on_error EXIT

# Main execution
main() {
    echo ""
    echo -e "${BLUE}🚀 Starting AccessWash Platform...${NC}"
    echo ""
    
    check_prerequisites
    cleanup_services
    start_docker
    setup_django
    start_tunnel
    start_logs
    show_status
    
    success "Startup completed successfully!"
    log "All services running. Use 'tail -f $LOG_FILE' to monitor."
}

main "$@"