#!/bin/bash

# AccessWash Platform Startup Script
# This script starts Docker containers (web, db, redis) and Cloudflare tunnel, with live logging
# Services persist after Ctrl+C or terminal closure
# Run with --no-logs to skip live logging and run fully in background

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration (use environment variables with defaults)
TUNNEL_ID="${TUNNEL_ID:-77255734-999d-4f75-9663-e8b10d671c16}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
DB_CHECK_TABLE="${DB_CHECK_TABLE:-public.auth_user}"  # Table to check for DB existence
DB_CONTAINER_NAME="${DB_CONTAINER_NAME:-db}"  # Name of the database container
LOG_FILE="${LOG_FILE:-accesswash_startup.log}"  # Centralized log file
TUNNEL_LOG_FILE="tunnel.log"
DOCKER_LOG_FILE="docker.log"

# Command-line flags
FORCE_DB_SETUP=false
NO_LOGS=false
while [[ "$1" == --* ]]; do
    case "$1" in
        --force-db-setup) FORCE_DB_SETUP=true ;;
        --no-logs) NO_LOGS=true ;;
        *) print_error "Unknown option: $1"; exit 1 ;;
    esac
    shift
done

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]$(date '+%Y-%m-%d %H:%M:%S') ${NC} $1" | tee -a "$LOG_FILE"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]$(date '+%Y-%m-%d %H:%M:%S') ${NC} $1" | tee -a "$LOG_FILE"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]$(date '+%Y-%m-%d %H:%M:%S') ${NC} $1" | tee -a "$LOG_FILE"
}

print_error() {
    echo -e "${RED}[ERROR]$(date '+%Y-%m-%d %H:%M:%S') ${NC} $1" | tee -a "$LOG_FILE"
}

print_header() {
    echo -e "${PURPLE}========================================${NC}" | tee -a "$LOG_FILE"
    echo -e "${PURPLE}$1${NC}" | tee -a "$LOG_FILE"
    echo -e "${PURPLE}========================================${NC}" | tee -a "$LOG_FILE"
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

# Function to wait for database container to be ready
wait_for_db() {
    local max_attempts=30
    local attempt=1
    
    print_status "Waiting for database container to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        local db_container
        db_container=$(docker-compose ps -q "$DB_CONTAINER_NAME" 2>/dev/null)
        if [ -n "$db_container" ] && docker exec "$db_container" pg_isready -U accesswash_user -d accesswash_db >/dev/null 2>&1; then
            print_success "Database container is ready!"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "Database container failed to start after $max_attempts attempts"
    return 1
}

# Function to check if database is already initialized
check_database() {
    print_status "Checking if database is already initialized..."
    
    local db_container
    db_container=$(docker-compose ps -q "$DB_CONTAINER_NAME" 2>/dev/null)
    
    if [ -z "$db_container" ]; then
        print_warning "Database container not found. Assuming new database needed."
        return 1
    fi
    
    if docker exec "$db_container" psql -U accesswash_user -d accesswash_db -tAc \
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'auth_user')" | grep -q "t"; then
        print_success "Database already initialized (table $DB_CHECK_TABLE exists)."
        return 0
    else
        print_status "Database not initialized. Will set up new database."
        return 1
    fi
}

# Function to check prerequisites
check_prerequisites() {
    print_header "CHECKING PREREQUISITES"
    
    if ! command_exists docker; then
        print_error "Docker is not installed!"
        exit 1
    fi
    print_success "Docker found"
    
    if ! command_exists docker-compose; then
        print_error "Docker Compose is not installed!"
        exit 1
    fi
    print_success "Docker Compose found"
    
    if ! command_exists cloudflared; then
        print_error "Cloudflared is not installed!"
        print_status "Install with: wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb && sudo dpkg -i cloudflared-linux-amd64.deb"
        exit 1
    fi
    print_success "Cloudflared found"
    
    if [ ! -f "$COMPOSE_FILE" ]; then
        print_error "$COMPOSE_FILE not found! Make sure you're in the correct directory"
        exit 1
    fi
    print_success "Found $COMPOSE_FILE"
    
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
    
    print_status "Stopping Docker containers..."
    docker-compose down -v --remove-orphans || true
    print_success "Docker containers stopped"
    
    print_status "Stopping existing tunnel..."
    if [ -f tunnel.pid ] && ps -p $(cat tunnel.pid) >/dev/null; then
        kill $(cat tunnel.pid) || true
        rm -f tunnel.pid
    fi
    pkill -f "cloudflared tunnel" || true
    print_success "Existing tunnel stopped"
    
    # Stop any existing log tailing processes
    pkill -f "tail.*$DOCKER_LOG_FILE" || true
    pkill -f "tail.*$TUNNEL_LOG_FILE" || true
}

# Function to start Docker services
start_docker() {
    print_header "STARTING DOCKER SERVICES"
    
    print_status "Building and starting Docker containers..."
    docker-compose up --build -d || {
        print_error "Failed to start Docker containers"
        exit 1
    }
    
    print_status "Checking container status..."
    docker-compose ps | tee -a "$LOG_FILE"
    
    wait_for_db
    wait_for_service "Django" "http://localhost:8000/health/"
    
    print_success "Docker services started successfully"
}

# Function to set up Django
setup_django() {
    print_header "SETTING UP DJANGO"
    
    if [ "$FORCE_DB_SETUP" = false ] && check_database; then
        print_success "Skipping Django setup (database already initialized). Use --force-db-setup to override."
        return 0
    fi
    
    print_status "Running database migrations..."
    local max_attempts=3
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if docker-compose exec -T web python manage.py migrate_schemas --shared; then
            print_success "Database migrations completed"
            break
        else
            print_warning "Shared migrations failed (attempt $attempt/$max_attempts). Retrying..."
            sleep 5
            attempt=$((attempt + 1))
        fi
    done
    if [ $attempt -gt $max_attempts ]; then
        print_error "Database migrations failed after $max_attempts attempts"
        exit 1
    fi
    
    print_status "Creating demo data..."
    if docker-compose exec -T web python setup_data.py; then
        print_success "Demo data created"
    else
        print_warning "Demo data creation failed, but continuing..."
    fi
    
    print_success "Django setup completed"
}

# Function to start Cloudflare tunnel
start_tunnel() {
    print_header "STARTING CLOUDFLARE TUNNEL"
    
    mkdir -p ~/.cloudflared
    
    if [ ! -f ~/.cloudflared/config.yml ]; then
        print_status "Creating tunnel configuration..."
        cat > ~/.cloudflared/config.yml << EOF
tunnel: $TUNNEL_ID
credentials-file: ~/.cloudflared/$TUNNEL_ID.json
logfile: $TUNNEL_LOG_FILE
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
    
    print_status "Validating tunnel configuration..."
    if ! cloudflared tunnel --config ~/.cloudflared/config.yml ingress validate; then
        print_error "Invalid tunnel configuration"
        exit 1
    fi
    
    print_status "Starting Cloudflare tunnel..."
    nohup cloudflared tunnel --config ~/.cloudflared/config.yml run > "$TUNNEL_LOG_FILE" 2>&1 &
    local tunnel_pid=$!
    echo $tunnel_pid > tunnel.pid
    disown $tunnel_pid  # Detach tunnel process from terminal
    
    sleep 5
    if ps -p $tunnel_pid >/dev/null; then
        print_success "Cloudflare tunnel started successfully (PID: $tunnel_pid)"
    else
        print_error "Failed to start Cloudflare tunnel"
        cat "$TUNNEL_LOG_FILE" | tee -a "$LOG_FILE"
        exit 1
    fi
}

# Function to start background log collection
start_log_collection() {
    print_status "Starting background log collection..."
    
    # Start Docker log collection in background
    nohup docker-compose logs -f --tail=100 > "$DOCKER_LOG_FILE" 2>&1 &
    local docker_log_pid=$!
    echo $docker_log_pid > docker_logs.pid
    disown $docker_log_pid
    
    print_success "Background log collection started (Docker logs PID: $docker_log_pid)"
}

# Function to stream live logs with proper signal handling
stream_logs() {
    print_header "STREAMING LIVE LOGS"
    print_status "Streaming logs from Docker containers and Cloudflare tunnel"
    print_status "Press Ctrl+C to stop log streaming (services will continue running)"
    print_status "Logs are saved to $LOG_FILE, $DOCKER_LOG_FILE, and $TUNNEL_LOG_FILE"
    
    # Create a function to handle signals gracefully
    handle_log_interrupt() {
        echo ""
        print_warning "Log streaming stopped by user. Services continue running in background."
        print_status "To view logs later:"
        echo -e "  Docker: ${YELLOW}tail -f $DOCKER_LOG_FILE${NC}"
        echo -e "  Tunnel: ${YELLOW}tail -f $TUNNEL_LOG_FILE${NC}"
        echo -e "  Script: ${YELLOW}tail -f $LOG_FILE${NC}"
        echo ""
        show_final_status
        exit 0
    }
    
    # Set up signal handling for log streaming only
    trap handle_log_interrupt INT TERM
    
    # Stream logs from both sources, but handle interruption gracefully
    (
        # Use tail to follow both log files
        tail -f "$TUNNEL_LOG_FILE" 2>/dev/null &
        tail -f "$DOCKER_LOG_FILE" 2>/dev/null &
        wait
    ) || true  # Don't exit on interrupt
}

# Function to test the deployment
test_deployment() {
    print_header "TESTING DEPLOYMENT"
    
    print_status "Testing local endpoints..."
    if curl -s http://localhost:8000/health/ | grep -q "AccessWash"; then
        print_success "Local health check passed"
    else
        print_error "Local health check failed"
    fi
    
    print_status "Waiting for tunnel to propagate..."
    sleep 10
    
    print_status "Testing live endpoints..."
    if curl -s https://api.accesswash.org/health/ | grep -q "AccessWash"; then
        print_success "API endpoint working"
    else
        print_warning "API endpoint not responding yet (DNS propagation?)"
    fi
    
    if curl -s https://demo.accesswash.org/health/ | grep -q "AccessWash"; then
        print_success "Demo endpoint working"
    else
        print_warning "Demo endpoint not responding yet (DNS propagation?)"
    fi
}

# Function to show status and URLs
show_status() {
    print_header "ACCESSWASH PLATFORM STATUS"
    
    echo -e "${GREEN}🎉 AccessWash Platform is running!${NC}" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    echo -e "${BLUE}📊 Docker Containers:${NC}" | tee -a "$LOG_FILE"
    docker-compose ps | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    echo -e "${BLUE}🌐 Live URLs:${NC}" | tee -a "$LOG_FILE"
    echo -e "  🏢 Platform Admin:  ${GREEN}https://api.accesswash.org/admin/${NC}" | tee -a "$LOG_FILE"
    echo -e "  🚰 Demo Utility:    ${GREEN}https://demo.accesswash.org/admin/${NC}" | tee -a "$LOG_FILE"
    echo -e "  📚 API Docs:        ${GREEN}https://demo.accesswash.org/api/docs/${NC}" | tee -a "$LOG_FILE"
    echo -e "  ❤️ Health Check:    ${GREEN}https://demo.accesswash.org/health/${NC}" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    echo -e "${BLUE}🔐 Login Credentials:${NC}" | tee -a "$LOG_FILE"
    echo -e "  Platform: ${YELLOW}kkimtai@gmail.com${NC} / ${YELLOW}Aspire2infinity${NC}" | tee -a "$LOG_FILE"
    echo -e "  Demo Manager: ${YELLOW}manager@nairobidemo.accesswash.org${NC} / ${YELLOW}Aspire2infinity${NC}" | tee -a "$LOG_FILE"
    echo -e "  Field Tech: ${YELLOW}field1@nairobidemo.accesswash.org${NC} / ${YELLOW}Aspire2infinity${NC}" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
}

# Function to show final status (called when exiting)
show_final_status() {
    echo -e "${BLUE}📝 View Logs:${NC}"
    echo -e "  Docker: ${YELLOW}tail -f $DOCKER_LOG_FILE${NC}"
    echo -e "  Tunnel: ${YELLOW}tail -f $TUNNEL_LOG_FILE${NC}"
    echo -e "  Script: ${YELLOW}tail -f $LOG_FILE${NC}"
    echo ""
    echo -e "${BLUE}🛑 Stop Services:${NC}"
    echo -e "  ${YELLOW}./stop_accesswash.sh${NC} or ${YELLOW}docker-compose down && pkill -f cloudflared${NC}"
    echo ""
    echo -e "${BLUE}🔄 Restart with Options:${NC}"
    echo -e "  Force DB Setup: ${YELLOW}./$(basename "$0") --force-db-setup${NC}"
    echo -e "  No Live Logs: ${YELLOW}./$(basename "$0") --no-logs${NC}"
}

# Function to handle cleanup on error exit only
cleanup_on_error() {
    if [[ $? -ne 0 ]]; then
        print_status "Cleaning up due to error..."
        if [ -f tunnel.pid ]; then
            print_status "Stopping tunnel process..."
            kill $(cat tunnel.pid) 2>/dev/null || true
            rm -f tunnel.pid
        fi
        if [ -f docker_logs.pid ]; then
            print_status "Stopping log collection..."
            kill $(cat docker_logs.pid) 2>/dev/null || true
            rm -f docker_logs.pid
        fi
        print_status "Stopping Docker containers..."
        docker-compose down -v --remove-orphans || true
        print_success "Cleanup completed"
    fi
}

# Set trap for cleanup only on error exit (not normal interrupts)
trap cleanup_on_error EXIT

# Main execution
main() {
    print_header "ACCESSWASH PLATFORM STARTUP"
    echo -e "${GREEN}Starting AccessWash Platform with live deployment...${NC}" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    
    echo "AccessWash Platform Startup Log - $(date '+%Y-%m-%d %H:%M:%S')" > "$LOG_FILE"
    
    check_prerequisites
    stop_services
    start_docker
    setup_django
    start_tunnel
    start_log_collection
    test_deployment
    show_status
    
    print_success "AccessWash Platform startup completed!"
    
    if [ "$NO_LOGS" = false ]; then
        stream_logs  # Stream live logs with proper signal handling
    else
        print_status "Skipping live logs (--no-logs specified)."
        show_final_status
        print_success "AccessWash Platform is running in background. Check log files for status."
    fi
}

# Run main function
main "$@"