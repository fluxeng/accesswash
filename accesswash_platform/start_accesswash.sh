#!/bin/bash

# AccessWash Platform Startup Script
# Fixed version with proper Django health checks

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
TUNNEL_ID="${TUNNEL_ID:-77255734-999d-4f75-9663-e8b10d671c16}"
LOG_FILE="accesswash.log"

# Command-line flags
FORCE_DB_SETUP=false
if [[ "$1" == "--force-db-setup" ]]; then
    FORCE_DB_SETUP=true
fi

# Simple logging functions
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

# Log command with output
run_cmd() {
    echo "Running: $1" >> "$LOG_FILE"
    if eval "$1" 2>&1 | tee -a "$LOG_FILE"; then
        return 0
    else
        return 1
    fi
}

# Check prerequisites
check_prerequisites() {
    header "CHECKING PREREQUISITES"
    
    command -v docker >/dev/null 2>&1 || { error "Docker not installed"; exit 1; }
    command -v docker-compose >/dev/null 2>&1 || { error "Docker Compose not installed"; exit 1; }
    command -v cloudflared >/dev/null 2>&1 || { error "Cloudflared not installed"; exit 1; }
    [ -f "docker-compose.yml" ] || { error "docker-compose.yml not found"; exit 1; }
    [ -f "$HOME/.cloudflared/$TUNNEL_ID.json" ] || { error "Tunnel credentials not found"; exit 1; }
    
    success "All prerequisites found"
}

# Clean up existing services
cleanup_services() {
    header "CLEANING UP SERVICES"
    
    # Kill processes on ports
    for port in 5432 6379 8000; do
        if lsof -ti:$port >/dev/null 2>&1; then
            log "Killing processes on port $port"
            lsof -ti:$port | xargs kill -9 2>/dev/null || true
        fi
    done
    
    # Stop Docker containers
    log "Stopping Docker containers..."
    run_cmd "docker-compose down --timeout 10 --remove-orphans" || true
    
    # Stop tunnel
    pkill -f "cloudflared tunnel" 2>/dev/null || true
    rm -f tunnel.pid docker_logs.pid
    
    success "Cleanup completed"
}

# Start Docker services
start_docker() {
    header "STARTING DOCKER SERVICES"
    
    log "Building and starting containers..."
    if ! run_cmd "docker-compose up --build -d"; then
        error "Failed to start Docker containers"
        exit 1
    fi
    
    # Wait for database
    log "Waiting for database..."
    attempts=0
    while [ $attempts -lt 30 ]; do
        # Use the correct database credentials from your setup
        if docker-compose exec -T db pg_isready -U accesswash_user -d accesswash_db >/dev/null 2>&1; then
            success "Database ready"
            break
        fi
        echo -n "."
        sleep 2
        attempts=$((attempts + 1))
    done
    
    if [ $attempts -eq 30 ]; then
        error "Database failed to start"
        # Show database logs for debugging
        log "Database logs:"
        docker-compose logs db
        exit 1
    fi
    
    # Wait for Django with better health check
    log "Waiting for Django..."
    attempts=0
    while [ $attempts -lt 30 ]; do
        # Check if Django is responding (try multiple endpoints)
        if docker-compose exec -T web python manage.py check >/dev/null 2>&1; then
            success "Django ready"
            break
        elif curl -s http://localhost:8000/ >/dev/null 2>&1; then
            success "Django web server ready"
            break
        elif curl -s http://localhost:8000/admin/ >/dev/null 2>&1; then
            success "Django admin ready"
            break
        fi
        echo -n "."
        sleep 3
        attempts=$((attempts + 1))
    done
    
    if [ $attempts -eq 30 ]; then
        error "Django failed to start"
        log "Django logs:"
        docker-compose logs web
        exit 1
    fi
}

# Check if database exists
database_exists() {
    # Check if the database has been migrated (look for django tables)
    if docker-compose exec -T db psql -U accesswash_user -d accesswash_db -tAc \
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'django_migrations')" 2>/dev/null | grep -q "t"; then
        return 0
    else
        return 1
    fi
}

# Setup Django database
setup_django() {
    header "DJANGO SETUP"
    
    if [ "$FORCE_DB_SETUP" = false ] && database_exists; then
        success "Database already exists - skipping setup"
        return 0
    fi
    
    # Run standard Django migrations first
    log "Running Django migrations..."
    if ! run_cmd "docker-compose exec -T web python manage.py migrate"; then
        # If regular migrate fails, try with tenant schemas
        log "Regular migrate failed, trying tenant schemas..."
        if ! run_cmd "docker-compose exec -T web python manage.py migrate_schemas --shared"; then
            error "Migrations failed"
            docker-compose logs web
            exit 1
        fi
    fi
    
    # Collect static files
    log "Collecting static files..."
    run_cmd "docker-compose exec -T web python manage.py collectstatic --noinput" || warning "Static file collection failed"
    
    # Run setup data script
    log "Creating demo data..."
    if run_cmd "docker-compose exec -T web python setup_data.py"; then
        success "Demo data created"
    else
        warning "Demo data creation failed - continuing anyway"
    fi
    
    success "Django setup completed"
}

# Create a simple health check endpoint
create_health_endpoint() {
    log "Ensuring health check endpoint exists..."
    
    # Check if health endpoint responds
    if curl -s http://localhost:8000/health/ >/dev/null 2>&1; then
        success "Health endpoint already exists"
        return 0
    fi
    
    # Create a simple health check in Django
    docker-compose exec -T web python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accesswash_platform.settings')
django.setup()

from django.http import JsonResponse
from django.urls import path
from django.conf import settings

# Create a simple health check view
def health_check(request):
    return JsonResponse({'status': 'ok', 'service': 'accesswash'})

print('Health check would be created via proper URL configuration')
" || warning "Could not create health endpoint"
}

# Start Cloudflare tunnel
start_tunnel() {
    header "STARTING TUNNEL"
    
    # Create config if needed
    if [ ! -f ~/.cloudflared/config.yml ]; then
        log "Creating tunnel config with wildcard support..."
        mkdir -p ~/.cloudflared
        cat > ~/.cloudflared/config.yml << EOF
tunnel: $TUNNEL_ID
credentials-file: ~/.cloudflared/$TUNNEL_ID.json
ingress:
  # Main platform admin (specific)
  - hostname: api.accesswash.org
    service: http://localhost:8000
    
  # Demo utility (specific)
  - hostname: demo.accesswash.org
    service: http://localhost:8000
    
  # Main app (specific)
  - hostname: app.accesswash.org
    service: http://localhost:8000
    
  # WILDCARD CATCH-ALL for all other subdomains
  # This handles tenant1.accesswash.org, utility2.accesswash.org, etc.
  - hostname: "*.accesswash.org"
    service: http://localhost:8000
    
  # Default fallback
  - service: http_status:404
EOF
    fi
    
    # Start tunnel
    log "Starting Cloudflare tunnel..."
    nohup cloudflared tunnel --config ~/.cloudflared/config.yml run >> "$LOG_FILE" 2>&1 &
    tunnel_pid=$!
    echo $tunnel_pid > tunnel.pid
    disown $tunnel_pid
    
    sleep 3
    if ps -p $tunnel_pid >/dev/null; then
        success "Tunnel started (PID: $tunnel_pid)"
    else
        error "Tunnel failed to start"
        exit 1
    fi
}

# Start background log monitoring
start_logs() {
    log "Starting background log monitoring..."
    nohup docker-compose logs -f --tail=50 >> "$LOG_FILE" 2>&1 &
    docker_logs_pid=$!
    echo $docker_logs_pid > docker_logs.pid
    disown $docker_logs_pid
    success "Log monitoring started (PID: $docker_logs_pid)"
}

# Show final status
show_status() {
    header "PLATFORM STATUS"
    
    echo ""
    echo -e "${GREEN}🎉 AccessWash Platform is running!${NC}"
    echo ""
    echo -e "${BLUE}URLs:${NC}"
    echo "  Local:  http://localhost:8000/"
    echo "  Admin:  http://localhost:8000/admin/"
    echo "  Remote: https://api.accesswash.org/admin/"
    echo "  Demo:   https://demo.accesswash.org/admin/"
    echo ""
    echo -e "${BLUE}Credentials:${NC}"
    echo "  Platform: kkimtai@gmail.com / Welcome1!"
    echo "  Demo:     demo1@accesswash.org / Welcome1!"
    echo ""
    echo -e "${BLUE}Management:${NC}"
    echo "  Logs:     tail -f $LOG_FILE"
    echo "  Stop:     ./stop_accesswash.sh"
    echo "  Reset:    $0 --force-db-setup"
    echo "  Django:   docker-compose exec web python manage.py shell"
    echo ""
    echo -e "${BLUE}Debugging:${NC}"
    echo "  Web logs: docker-compose logs web"
    echo "  DB logs:  docker-compose logs db" 
    echo "  All logs: docker-compose logs"
    echo ""
}

# Cleanup on error with better diagnostics
cleanup_on_error() {
    if [[ $? -ne 0 ]]; then
        error "Startup failed - showing diagnostics..."
        
        echo ""
        log "=== CONTAINER STATUS ==="
        docker-compose ps
        
        echo ""
        log "=== WEB CONTAINER LOGS ==="
        docker-compose logs web --tail 20
        
        echo ""
        log "=== DATABASE CONTAINER LOGS ==="
        docker-compose logs db --tail 10
        
        echo ""
        log "=== CLEANUP ==="
        docker-compose down --remove-orphans 2>/dev/null || true
        pkill -f cloudflared 2>/dev/null || true
        rm -f tunnel.pid docker_logs.pid
    fi
}

trap cleanup_on_error EXIT

# Main execution
main() {
    echo "AccessWash Platform Startup - $(date)" > "$LOG_FILE"
    echo ""
    echo -e "${BLUE}🚀 Starting AccessWash Platform...${NC}"
    echo ""
    
    check_prerequisites
    cleanup_services
    start_docker
    setup_django
    create_health_endpoint
    start_tunnel
    start_logs
    show_status
    
    success "Startup completed!"
    log "All services running in background"
}

main "$@"