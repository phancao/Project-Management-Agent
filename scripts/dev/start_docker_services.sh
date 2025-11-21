#!/bin/bash
# Start Docker Services Script
# Loads API key from conf.yaml and starts Docker services

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to extract API key from conf.yaml
extract_api_key_from_config() {
    local config_file="$PROJECT_ROOT/conf.yaml"
    
    if [ ! -f "$config_file" ]; then
        echo -e "${YELLOW}⚠️  conf.yaml not found, using environment variable if set${NC}"
        return 1
    fi
    
    # Try to extract using Python (most reliable)
    if command_exists python3; then
        local api_key=$(python3 -c "
import yaml
import sys
try:
    with open('$config_file', 'r') as f:
        config = yaml.safe_load(f)
        api_key = config.get('BASIC_MODEL', {}).get('api_key', '')
        if api_key:
            print(api_key)
            sys.exit(0)
        else:
            sys.exit(1)
except Exception as e:
    sys.exit(1)
" 2>/dev/null)
        
        if [ $? -eq 0 ] && [ -n "$api_key" ]; then
            export OPENAI_API_KEY="$api_key"
            echo -e "${GREEN}✅ Loaded API key from conf.yaml${NC}"
            return 0
        fi
    fi
    
    # Fallback: try to extract using grep/awk (less reliable but works for simple YAML)
    local api_key=$(grep -A 3 "BASIC_MODEL:" "$config_file" 2>/dev/null | grep "api_key:" | sed -n 's/.*api_key:[[:space:]]*\(.*\)/\1/p' | tr -d '"' | tr -d "'" | xargs)
    
    if [ -n "$api_key" ] && [ "$api_key" != "null" ]; then
        export OPENAI_API_KEY="$api_key"
        echo -e "${GREEN}✅ Loaded API key from conf.yaml${NC}"
        return 0
    fi
    
    echo -e "${YELLOW}⚠️  Could not extract API key from conf.yaml, using environment variable if set${NC}"
    return 1
}

echo "=========================================="
echo "   Starting Docker Services"
echo "=========================================="
echo ""

# Load API key from conf.yaml
echo -e "${BLUE}Loading configuration from conf.yaml...${NC}"
extract_api_key_from_config
echo ""

# Check if docker-compose is available
if ! command_exists docker-compose && ! command_exists docker; then
    echo -e "${RED}❌ docker-compose or docker not found${NC}"
    exit 1
fi

# Determine which command to use
if command_exists docker-compose; then
    DOCKER_CMD="docker-compose"
elif docker compose version >/dev/null 2>&1; then
    DOCKER_CMD="docker compose"
else
    echo -e "${RED}❌ docker-compose not available${NC}"
    exit 1
fi

# Start Docker services
echo -e "${BLUE}Starting Docker services...${NC}"
$DOCKER_CMD up -d "$@"

echo ""
echo "=========================================="
echo -e "${GREEN}✅ Docker services started${NC}"
echo ""
echo "To view logs: $DOCKER_CMD logs -f"
echo "To stop services: $DOCKER_CMD down"
echo "=========================================="

