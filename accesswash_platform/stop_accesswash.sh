#!/bin/bash

# AccessWash Platform Stop Script
# Simple, clean shutdown of all services

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
LOG_FILE="accesswash_shutdown.log"

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

# Initialize log file
echo "AccessWash Platform Shutdown - $(date)" > "$LOG_FILE"

header "STOPPING ACCESSWASH PLATFORM"

# Check Docker
if ! docker info >/dev/null 2>&1; then
    error "Docker not running"
    exit 1
fi

# Stop background log monitoring
log "Stopping background processes..."
if [ -f docker_logs.pid ]; then
    log_pid=$(cat docker_logs.pid 2>/dev/null)
    if [ -n "$log_pid" ] && ps -p "$log_pid" >/dev/null 2>&1; then
        kill "$log_pid" 2>/dev/null || true
        success "Log monitoring stopped"
    fi
    rm -f docker_logs.pid
fi

# Stop Docker containers
log "Stopping Docker containers..."
if docker-compose ps 2>/dev/null | grep -q "Up"; then
    if docker-compose down -v --remove-orphans 2>&1 | tee -a "$LOG_FILE"; then
        success "Docker containers stopped"
    else
        warning "Some containers failed to stop gracefully"
        docker stop $(docker ps -q) 2>/dev/null || true
    fi
else
    log "No running containers found"
fi

# Verify critical services stopped
for service in redis db web; do
    if docker ps -q -f name=$service 2>/dev/null | grep -q .; then
        warning "$service still running, force stopping..."
        docker stop $(docker ps -q -f name=$service) 2>/dev/null || true
    else
        success "$service stopped"
    fi
done

# Stop Cloudflare tunnel
log "Stopping Cloudflare tunnel..."
if [ -f tunnel.pid ]; then
    tunnel_pid=$(cat tunnel.pid 2>/dev/null)
    if [ -n "$tunnel_pid" ] && ps -p "$tunnel_pid" >/dev/null 2>&1; then
        kill "$tunnel_pid" 2>/dev/null || true
        success "Tunnel stopped (PID: $tunnel_pid)"
    fi
    rm -f tunnel.pid
fi

# Kill remaining tunnel processes
if pgrep -f "cloudflared tunnel" >/dev/null; then
    pkill -f "cloudflared tunnel" 2>/dev/null || true
    success "Remaining tunnel processes stopped"
fi

# Clean up ports
log "Cleaning up ports..."
for port in 5432 6379 8000; do
    if lsof -ti:$port >/dev/null 2>&1; then
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
        success "Port $port cleared"
    fi
done

# Final verification
header "SHUTDOWN COMPLETE"

remaining_containers=$(docker ps -q | wc -l)
remaining_tunnels=$(pgrep -f cloudflared | wc -l)

echo ""
echo -e "${GREEN}🛑 AccessWash Platform stopped successfully${NC}"
echo ""
echo -e "${BLUE}System Status:${NC}"
echo "  Docker containers: $remaining_containers running"
echo "  Tunnel processes: $remaining_tunnels running"
echo ""
echo -e "${BLUE}Files:${NC}"
echo "  Shutdown log: $LOG_FILE"
echo "  Startup log: accesswash.log"
echo ""
echo -e "${BLUE}To restart:${NC}"
echo "  ./start_accesswash.sh"
echo "  ./start_accesswash.sh --force-db-setup"
echo ""

success "Platform shutdown completed"