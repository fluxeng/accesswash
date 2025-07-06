#!/bin/bash

# AccessWash Platform Stop Script
# This script stops all Docker containers and Cloudflare tunnel

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_header() {
    echo -e "${YELLOW}========================================${NC}"
    echo -e "${YELLOW}$1${NC}"
    echo -e "${YELLOW}========================================${NC}"
}

print_header "STOPPING ACCESSWASH PLATFORM"

# Stop Docker containers
print_status "Stopping Docker containers..."
docker-compose down -v || true
print_success "Docker containers stopped"

# Stop Cloudflare tunnel
print_status "Stopping Cloudflare tunnel..."

# Kill tunnel by PID if file exists
if [ -f tunnel.pid ]; then
    if ps -p $(cat tunnel.pid) > /dev/null; then
        kill $(cat tunnel.pid)
        print_success "Tunnel stopped (PID: $(cat tunnel.pid))"
    fi
    rm -f tunnel.pid
fi

# Kill any remaining cloudflared processes
pkill -f "cloudflared tunnel" || true

# Clean up log files
rm -f tunnel.log

print_success "All AccessWash services stopped"
echo -e "${GREEN}🛑 AccessWash Platform has been shut down${NC}"