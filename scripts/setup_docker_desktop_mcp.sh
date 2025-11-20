#!/bin/bash
# Setup script for Docker Desktop MCP Toolkit with PM MCP Server

set -e

echo "=========================================="
echo "Docker Desktop MCP Toolkit Setup"
echo "=========================================="
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker Desktop first."
    exit 1
fi

echo "✅ Docker is installed: $(docker --version)"
echo ""

# Check if image exists
if docker images | grep -q "pm-mcp-server.*latest"; then
    echo "✅ PM MCP Server image found:"
    docker images | grep "pm-mcp-server.*latest"
else
    echo "📦 Building PM MCP Server image..."
    docker build -f Dockerfile.mcp-server -t pm-mcp-server:latest .
    echo "✅ Image built successfully"
fi

echo ""
echo "=========================================="
echo "Configuration Summary"
echo "=========================================="
echo ""
echo "Image Name: pm-mcp-server:latest"
echo "Transport: SSE"
echo "URL: http://localhost:8080/sse"
echo "Port: 8080"
echo ""
echo "Environment Variables:"
echo "  DATABASE_URL=postgresql://pm_user:pm_password@postgres:5432/project_management"
echo "  LOG_LEVEL=INFO"
echo "  ENABLE_AUTH=false"
echo "  ENABLE_RBAC=false"
echo "  MCP_TRANSPORT=sse"
echo "  MCP_HOST=0.0.0.0"
echo "  MCP_PORT=8080"
echo ""
echo "=========================================="
echo "Next Steps"
echo "=========================================="
echo ""
echo "1. Open Docker Desktop"
echo "2. Go to Settings → Extensions → MCP"
echo "3. Click 'Add Server' or '+'"
echo "4. Configure with the settings above"
echo "5. Save and start the server"
echo ""
echo "For detailed instructions, see: docs/DOCKER_DESKTOP_MCP_SETUP.md"
echo ""
echo "To test after setup:"
echo "  curl http://localhost:8080/health"
echo "  curl -X POST http://localhost:8080/tools/list -H 'Content-Type: application/json' -d '{}'"
echo ""










