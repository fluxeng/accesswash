#!/bin/bash

# AccessWash Platform Stop Script
# This script stops all Docker containers (including Redis and PostgreSQL) and Cloudflare tunnel

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Log file for shutdown activities
LOG_FILE="accesswash_shutdown.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

print_header() {
    echo -e "${YELLOW}========================================${NC}" | tee -a "$LOG_FILE"
    echo -e "${YELLOW}$1${NC}" | tee -a "$LOG_FILE"
    echo -e "${YELLOW}========================================${NC}" | tee -a "$LOG_FILE"
}

# Initialize log file
echo "[$TIMESTAMP] Starting AccessWash shutdown" > "$LOG_FILE"

print_header "STOPPING ACCESSWASH PLATFORM"

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Stop Docker containers (web, db, redis)
print_status "Stopping Docker containers (web, db, redis)..."
if docker-compose ps | grep -q "Up"; then
    docker-compose down -v --remove-orphans || {
        print_error "Failed to stop Docker containers"
        exit 1
    }
    print_success "Docker containers stopped"
else
    print_status "No running Docker containers found"
fi

# Verify Redis is stopped
print_status "Verifying Redis service is stopped..."
if docker ps -q -f name=redis | grep -q .; then
    print_error "Redis container is still running"
    docker stop redis || print_error "Failed to stop Redis container"
else
    print_success "Redis service is stopped"
fi

# Verify PostgreSQL is stopped
print_status "Verifying PostgreSQL service is stopped..."
if docker ps -q -f name=db | grep -q .; then
    print_error "PostgreSQL container is still running"
    docker stop db || print_error "Failed to stop PostgreSQL container"
else
    print_success "PostgreSQL service is stopped"
fi

# Stop Cloudflare tunnel
print_status "Stopping Cloudflare tunnel..."
TUNNEL_PID_FILE="tunnel.pid"
TUNNEL_LOG_FILE="tunnel.log"

if [ -f "$TUNNEL_PID_FILE" ]; then
    TUNNEL_PID=$(cat "$TUNNEL_PID_FILE" 2>/dev/null)
    if [ -n "$TUNNEL_PID" ] && ps -p "$TUNNEL_PID" >/dev/null 2>&1; then
        kill "$TUNNEL_PID" && print_success "Tunnel stopped (PID: $TUNNEL_PID)"
    else
        print_status "No running tunnel found for PID: $TUNNEL_PID"
    fi
    rm -f "$TUNNEL_PID_FILE"
else
    print_status "No tunnel PID file found"
fi

# Kill any remaining cloudflared processes
if pgrep -f "cloudflared tunnel" >/dev/null; then
    pkill -f "cloudflared tunnel" && print_success "Remaining cloudflared processes stopped"
else
    print_status "No remaining cloudflared processes found"
fi

# Clean up log files
if [ -f "$TUNNEL_LOG_FILE" ]; then
    rm -f "$TUNNEL_LOG_FILE" && print_success "Tunnel log file cleaned"
else
    print_status "No tunnel log file found"
fi

# Final verification
print_status "Verifying all services are stopped..."
if docker ps -q | grep -q .; then
    print_error "Some Docker containers are still running"
    docker ps -a
    exit 1
else
    print_success "All Docker services are stopped"
fi

if pgrep -f "cloudflared tunnel" >/dev/null; then
    print_error "Cloudflare tunnel processes are still running"
    exit 1
else
    print_success "All Cloudflare tunnel processes are stopped"
fi

print_success "All AccessWash services stopped successfully"
echo -e "${GREEN}🛑 AccessWash Platform has been shut down${NC}" | tee -a "$LOG_FILE"