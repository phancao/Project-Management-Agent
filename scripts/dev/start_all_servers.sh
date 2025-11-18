#!/bin/bash
# Start All Servers Script
# Starts all required services for the Project Management Agent

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "   Starting All Servers"
echo "=========================================="
echo ""

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 1. Start Docker services (OpenProject, PostgreSQL, etc.)
echo -e "${BLUE}1. Starting Docker Services...${NC}"
if command_exists docker-compose; then
    echo "   Starting OpenProject, PostgreSQL, and other Docker services..."
    docker-compose up -d openproject_db openproject postgres 2>&1 | grep -v "level=warning" || true
    echo -e "${GREEN}   ✅ Docker services started${NC}"
else
    echo -e "${YELLOW}   ⚠️ docker-compose not found, skipping Docker services${NC}"
fi
echo ""

# 2. Start Backend Server
echo -e "${BLUE}2. Starting Backend Server...${NC}"
if pgrep -f "python.*server.py" > /dev/null; then
    echo -e "${YELLOW}   ⚠️ Backend server is already running${NC}"
else
    echo "   Starting backend on http://localhost:8000..."
    if command_exists uv; then
        nohup uv run python server.py --host localhost --port 8000 --log-level info > /tmp/deerflow_server.log 2>&1 &
        echo $! > /tmp/deerflow_server.pid
        sleep 3
        echo -e "${GREEN}   ✅ Backend server started (PID: $(cat /tmp/deerflow_server.pid))${NC}"
        echo "   Logs: tail -f /tmp/deerflow_server.log"
    else
        echo -e "${YELLOW}   ⚠️ 'uv' not found, please start backend manually${NC}"
    fi
fi
echo ""

# 3. Start Frontend Server
echo -e "${BLUE}3. Starting Frontend Server...${NC}"
if pgrep -f "next.*dev" > /dev/null || pgrep -f "node.*next" > /dev/null; then
    echo -e "${YELLOW}   ⚠️ Frontend server is already running${NC}"
else
    if [ -d "web" ]; then
        echo "   Starting frontend on http://localhost:3000..."
        cd web
        if command_exists npm; then
            nohup npm run dev > /tmp/frontend_server.log 2>&1 &
            echo $! > /tmp/frontend_server.pid
            cd ..
            sleep 5
            echo -e "${GREEN}   ✅ Frontend server started (PID: $(cat /tmp/frontend_server.pid))${NC}"
            echo "   Logs: tail -f /tmp/frontend_server.log"
        else
            echo -e "${YELLOW}   ⚠️ 'npm' not found, please start frontend manually${NC}"
            cd ..
        fi
    else
        echo -e "${YELLOW}   ⚠️ 'web' directory not found${NC}"
    fi
fi
echo ""

echo "=========================================="
echo -e "${GREEN}✅ Server Startup Complete!${NC}"
echo ""
echo "Waiting for services to be ready..."
sleep 5

# Run the checklist
if [ -f "$SCRIPT_DIR/check_servers.sh" ]; then
    echo ""
    "$SCRIPT_DIR/check_servers.sh"
else
    echo ""
    echo "To verify all services are running, use:"
    echo "  ./scripts/check_servers.sh"
fi
