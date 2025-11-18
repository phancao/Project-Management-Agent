#!/bin/bash
# Server Checklist Script
# Verifies all required services are running before testing

set -e

# Get project root directory (parent of scripts/)
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_ROOT"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Service status tracking
ALL_SERVICES_OK=true

echo "=========================================="
echo "   Server Availability Checklist"
echo "=========================================="
echo ""

# Function to check if a port is accessible
check_port() {
    local service_name=$1
    local host=$2
    local port=$3
    local timeout=${4:-2}
    
    if nc -z -w $timeout $host $port 2>/dev/null; then
        echo -e "${GREEN}✅${NC} $service_name (${host}:${port}) - Running"
        return 0
    else
        echo -e "${RED}❌${NC} $service_name (${host}:${port}) - Not accessible"
        ALL_SERVICES_OK=false
        return 1
    fi
}

# Function to check HTTP endpoint
check_http() {
    local service_name=$1
    local url=$2
    local expected_status=${3:-200}
    
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null || echo "000")
    
    if [ "$http_code" = "$expected_status" ] || [ "$http_code" = "302" ] || [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✅${NC} $service_name ($url) - Responding (HTTP $http_code)"
        return 0
    else
        echo -e "${RED}❌${NC} $service_name ($url) - Not responding (HTTP $http_code)"
        ALL_SERVICES_OK=false
        return 1
    fi
}

# Function to check Docker container
check_docker_container() {
    local container_name=$1
    local service_name=$2
    
    if docker ps --format '{{.Names}}' | grep -q "^${container_name}$"; then
        echo -e "${GREEN}✅${NC} $service_name (Docker: $container_name) - Running"
        return 0
    else
        echo -e "${RED}❌${NC} $service_name (Docker: $container_name) - Not running"
        ALL_SERVICES_OK=false
        return 1
    fi
}

echo -e "${BLUE}📋 Checking Services...${NC}"
echo ""

# 1. Check OpenProject
echo "1. OpenProject Service"
check_docker_container "project-management-agent-openproject-1" "OpenProject Container"
check_docker_container "project-management-agent-openproject_db-1" "OpenProject Database"
check_http "OpenProject Web" "http://localhost:8080" "302"
check_port "OpenProject Port" "localhost" "8080"
echo ""

# 2. Check Frontend
echo "2. Frontend Service"
check_port "Frontend Port" "localhost" "3000"
check_http "Frontend Web" "http://localhost:3000" "200"
echo ""

# 3. Check Backend
echo "3. Backend Service"
check_port "Backend Port" "localhost" "8000"
check_http "Backend API Docs" "http://localhost:8000/docs" "200"
check_http "Backend Health" "http://localhost:8000/api/pm/providers" "200"
echo ""

# 4. Check Database Services
echo "4. Database Services"
check_docker_container "project-management-agent-postgres-1" "PostgreSQL Container"
check_port "PostgreSQL Port" "localhost" "5432"
echo ""

# 5. Check Other Services (Redis, etc.)
echo "5. Other Services"

# Check if Redis is defined in docker-compose
if docker-compose config --services 2>/dev/null | grep -q "^redis$"; then
    # Find Redis container name (may vary)
    redis_container=$(docker ps --format '{{.Names}}' | grep -i redis | head -1)
    if [ -n "$redis_container" ]; then
        echo -e "${GREEN}✅${NC} Redis Container (Docker: $redis_container) - Running"
        check_port "Redis Port" "localhost" "6379" || true
    else
        # Check if Redis port is accessible (might be running elsewhere)
        if check_port "Redis Port" "localhost" "6379" 2; then
            echo -e "${YELLOW}⚠️${NC} Redis Container - Not found in Docker, but port is accessible"
        else
            echo -e "${YELLOW}⚠️${NC} Redis - Not running (optional service)"
        fi
    fi
else
    echo -e "${YELLOW}⚠️${NC} Redis - Not configured (optional)"
fi
echo ""

# Summary
echo "=========================================="
if [ "$ALL_SERVICES_OK" = true ]; then
    echo -e "${GREEN}✅ All Required Services Are Running!${NC}"
    echo ""
    echo "You can now proceed with testing."
    exit 0
else
    echo -e "${RED}❌ Some Services Are Not Available${NC}"
    echo ""
    echo "Please start the missing services before testing."
    echo ""
    echo "Quick Start Commands:"
    echo "  # Start all services with docker-compose"
    echo "  docker-compose up -d"
    echo ""
    echo "  # Start frontend"
    echo "  cd web && npm run dev"
    echo ""
    echo "  # Start backend"
    echo "  uv run python server.py --host localhost --port 8000"
    exit 1
fi
