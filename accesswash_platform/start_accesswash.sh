#!/bin/bash

# AccessWash Platform Startup Script - Simplified & Powerful
# Complete startup with robust error handling

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
TUNNEL_ID="${TUNNEL_ID:-5420642c-7326-407f-9fdc-0ec4285818c0}"
LOG_FILE="accesswash.log"

# Flags
FORCE_DB_SETUP=false
SKIP_TUNNEL=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --force-db-setup) FORCE_DB_SETUP=true; shift ;;
        --skip-tunnel) SKIP_TUNNEL=true; shift ;;
        --local-only) SKIP_TUNNEL=true; shift ;;
        -h|--help)
            echo "AccessWash Platform Startup"
            echo "Usage: $0 [--force-db-setup] [--skip-tunnel] [--local-only]"
            exit 0 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Logging
log() { echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"; }
success() { echo -e "${GREEN}✓${NC} $1" | tee -a "$LOG_FILE"; }
error() { echo -e "${RED}✗${NC} $1" | tee -a "$LOG_FILE"; }
warning() { echo -e "${YELLOW}⚠${NC} $1" | tee -a "$LOG_FILE"; }
header() { echo -e "\n${YELLOW}========== $1 ==========${NC}" | tee -a "$LOG_FILE"; }

# Initialize
echo "AccessWash Platform Startup - $(date)" > "$LOG_FILE"
echo -e "\n${BLUE}🚀 Starting AccessWash Platform...${NC}\n"

# Check prerequisites
check_prerequisites() {
    header "CHECKING PREREQUISITES"
    
    command -v docker >/dev/null 2>&1 || { error "Docker not installed"; exit 1; }
    command -v docker-compose >/dev/null 2>&1 || { error "Docker Compose not installed"; exit 1; }
    [ -f "docker-compose.yml" ] || { error "docker-compose.yml not found"; exit 1; }
    [ -f "manage.py" ] || { error "manage.py not found"; exit 1; }
    
    if [ "$SKIP_TUNNEL" = false ]; then
        command -v cloudflared >/dev/null 2>&1 || { error "Cloudflared not installed"; exit 1; }
        [ -f "$HOME/.cloudflared/$TUNNEL_ID.json" ] || { error "Tunnel credentials not found"; exit 1; }
    fi
    
    success "Prerequisites satisfied"
}

# Cleanup existing services
cleanup_services() {
    header "CLEANING UP"
    
    # Stop processes
    [ -f "tunnel.pid" ] && kill $(cat tunnel.pid) 2>/dev/null || true
    [ -f "docker_logs.pid" ] && kill $(cat docker_logs.pid) 2>/dev/null || true
    pkill -f "cloudflared tunnel" 2>/dev/null || true
    rm -f tunnel.pid docker_logs.pid
    
    # Clean ports
    for port in 5432 6379 8000; do
        lsof -ti:$port 2>/dev/null | xargs kill -9 2>/dev/null || true
    done
    
    # Stop containers
    docker-compose down --timeout 30 --remove-orphans 2>/dev/null || true
    [ "$FORCE_DB_SETUP" = true ] && docker-compose down -v 2>/dev/null || true
    
    success "Cleanup completed"
}

# Start Docker services
start_docker() {
    header "STARTING DOCKER SERVICES"
    
    log "Building and starting containers..."
    if ! docker-compose up --build -d 2>&1 | tee -a "$LOG_FILE"; then
        error "Failed to start containers"
        docker-compose logs --tail=20
        exit 1
    fi
    
    # Wait for database
    log "Waiting for database..."
    for i in {1..60}; do
        if docker-compose exec -T db pg_isready 2>/dev/null || \
           docker-compose exec -T db psql -U postgres -d postgres -c "SELECT 1" >/dev/null 2>&1 || \
           docker-compose exec -T db psql -U accesswash_user -d accesswash_db -c "SELECT 1" >/dev/null 2>&1; then
            success "Database ready"
            break
        fi
        [ $i -eq 60 ] && { error "Database timeout"; docker-compose logs db --tail=10; exit 1; }
        echo -n "."
        sleep 2
    done
    
    # Wait for Django
    log "Waiting for Django..."
    for i in {1..45}; do
        if docker-compose exec -T web python manage.py check >/dev/null 2>&1 || \
           curl -s -f http://localhost:8000/ >/dev/null 2>&1; then
            success "Django ready"
            break
        fi
        [ $i -eq 45 ] && { error "Django timeout"; docker-compose logs web --tail=20; exit 1; }
        echo -n "."
        sleep 3
    done
    
    success "Docker services started"
}

# Check if database exists
database_exists() {
    docker-compose exec -T db psql -U accesswash_user -d accesswash_db -tAc \
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'django_migrations')" 2>/dev/null | grep -q "t" || \
    docker-compose exec -T db psql -U postgres -d postgres -tAc \
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'django_migrations')" 2>/dev/null | grep -q "t"
}

# Setup Django
setup_django() {
    header "DJANGO SETUP"
    
    if [ "$FORCE_DB_SETUP" = false ] && database_exists; then
        success "Database exists - skipping setup"
        docker-compose exec -T web python manage.py collectstatic --noinput >/dev/null 2>&1 || true
        return 0
    fi
    
    log "Running migrations..."
    if ! docker-compose exec -T web python manage.py migrate --noinput 2>&1 | tee -a "$LOG_FILE"; then
        log "Trying tenant migrations..."
        if ! docker-compose exec -T web python manage.py migrate_schemas --shared 2>&1 | tee -a "$LOG_FILE"; then
            error "Migration failed"
            exit 1
        fi
    fi
    
    log "Creating superuser..."
    docker-compose exec -T web python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
if not User.objects.filter(email='kkimtai@gmail.com').exists():
    User.objects.create_superuser('kkimtai@gmail.com', 'Welcome1!')
    print('Superuser created')
" 2>/dev/null || warning "Superuser creation failed"
    
    log "Collecting static files..."
    docker-compose exec -T web python manage.py collectstatic --noinput >/dev/null 2>&1 || warning "Static files failed"
    
    log "Setting up demo data..."
    docker-compose exec -T web python setup_data.py 2>&1 | tee -a "$LOG_FILE" || warning "Demo data failed"
    
    success "Django setup completed"
}

# Start Cloudflare tunnel
start_tunnel() {
    [ "$SKIP_TUNNEL" = true ] && { warning "Skipping tunnel"; return 0; }
    
    header "STARTING TUNNEL"
    
    # Create config
    mkdir -p ~/.cloudflared
    cat > ~/.cloudflared/config.yml << EOF
tunnel: $TUNNEL_ID
credentials-file: $HOME/.cloudflared/$TUNNEL_ID.json

ingress:
  - hostname: api.accesswash.org
    service: http://localhost:8000
  - hostname: demo.accesswash.org
    service: http://localhost:8000
  - hostname: app.accesswash.org
    service: http://localhost:8000
  - hostname: "*.accesswash.org"
    service: http://localhost:8000
  - service: http_status:404
EOF
    
    # Validate and start
    cloudflared tunnel --config ~/.cloudflared/config.yml ingress validate || { error "Invalid tunnel config"; exit 1; }
    
    log "Starting tunnel..."
    nohup cloudflared tunnel --config ~/.cloudflared/config.yml run >> "$LOG_FILE" 2>&1 &
    tunnel_pid=$!
    echo $tunnel_pid > tunnel.pid
    disown $tunnel_pid
    
    sleep 5
    if ps -p $tunnel_pid >/dev/null; then
        success "Tunnel started (PID: $tunnel_pid)"
    else
        error "Tunnel failed to start"
        exit 1
    fi
}

# Start log monitoring
start_logs() {
    nohup docker-compose logs -f --tail=50 >> "$LOG_FILE" 2>&1 &
    echo $! > docker_logs.pid
    disown
}

# Show final status
show_status() {
    header "PLATFORM STATUS"
    
    echo -e "\n${GREEN}🎉 AccessWash Platform is running!${NC}\n"
    
    echo -e "${BLUE}Local Access:${NC}"
    echo "  Admin:  http://localhost:8000/admin/"
    echo "  Health: http://localhost:8000/"
    echo ""
    
    if [ "$SKIP_TUNNEL" = false ]; then
        echo -e "${BLUE}Remote Access:${NC}"
        echo "  Platform: https://api.accesswash.org/admin/"
        echo "  Demo:     https://demo.accesswash.org/admin/"
        echo ""
    fi
    
    echo -e "${BLUE}Credentials:${NC}"
    echo "  Email:    kkimtai@gmail.com"
    echo "  Password: Welcome1!"
    echo ""
    
    echo -e "${BLUE}Management:${NC}"
    echo "  Logs:    tail -f $LOG_FILE"
    echo "  Stop:    docker-compose down"
    echo "  Restart: $0 --force-db-setup"
    echo ""
    
    # Service status
    local web_status=$(docker-compose ps web 2>/dev/null | grep "Up" >/dev/null && echo "✅" || echo "❌")
    local db_status=$(docker-compose ps db 2>/dev/null | grep "Up" >/dev/null && echo "✅" || echo "❌")
    local tunnel_status="❌"
    [ "$SKIP_TUNNEL" = false ] && [ -f "tunnel.pid" ] && ps -p $(cat tunnel.pid) >/dev/null 2>&1 && tunnel_status="✅"
    
    echo -e "${BLUE}Services:${NC}"
    echo "  Django:  $web_status"
    echo "  Database: $db_status"
    echo "  Tunnel:   $tunnel_status"
    echo ""
}

# Error cleanup
cleanup_on_error() {
    if [[ $? -ne 0 ]]; then
        error "Startup failed - cleaning up..."
        docker-compose logs --tail=10 2>/dev/null || true
        docker-compose down --remove-orphans 2>/dev/null || true
        pkill -f cloudflared 2>/dev/null || true
        rm -f tunnel.pid docker_logs.pid
    fi
}

trap cleanup_on_error EXIT

# Main execution
main() {
    check_prerequisites
    cleanup_services
    start_docker
    setup_django
    start_tunnel
    start_logs
    show_status
    
    success "Startup completed!"
    echo "$(date): Success" > .accesswash_status
    trap - EXIT
}

main "$@"