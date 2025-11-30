"""
Unit tests for MCP Server SSE transport
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from mcp_server.config import PMServerConfig
from mcp_server.core.tool_context import ToolContext


@pytest.fixture
def mock_context():
    """Create a mock ToolContext."""
    context = MagicMock(spec=ToolContext)
    context.provider_manager = MagicMock()
    context.provider_manager.get_active_providers.return_value = []
    context.pm_service = AsyncMock()
    context.user_id = str(uuid4())
    return context


@pytest.fixture
def config():
    """Create a test config."""
    return PMServerConfig(
        server_name="Test Server",
        server_version="1.0.0"
    )


@pytest.fixture
def mock_mcp_server():
    """Create a mock MCP server instance."""
    server = MagicMock()
    server._tool_names = ["list_projects", "list_tasks"]
    return server


@pytest.fixture
def sse_app(mock_context, config, mock_mcp_server):
    """Create the SSE app for testing."""
    from mcp_server.transports.sse import create_sse_app
    return create_sse_app(mock_context, config, mock_mcp_server)


class TestSSETransportHealth:
    """Tests for SSE health endpoint."""
    
    def test_health_check_healthy(self, sse_app, mock_context, mock_mcp_server):
        """Test health check returns healthy status."""
        mock_context.provider_manager.get_active_providers.return_value = [
            MagicMock(id=uuid4(), name="Provider 1")
        ]
        
        client = TestClient(sse_app)
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["providers"] == 1
        assert data["tools"] == 2
    
    def test_health_check_no_providers(self, sse_app, mock_context, mock_mcp_server):
        """Test health check with no providers."""
        mock_context.provider_manager.get_active_providers.return_value = []
        
        client = TestClient(sse_app)
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["providers"] == 0


class TestSSETransportAppState:
    """Tests for SSE app state."""
    
    def test_app_has_context(self, sse_app, mock_context):
        """Test app has context in state."""
        assert sse_app.state.context == mock_context
    
    def test_app_has_config(self, sse_app, config):
        """Test app has config in state."""
        assert sse_app.state.config == config
    
    def test_app_has_mcp_server(self, sse_app, mock_mcp_server):
        """Test app has MCP server in state."""
        assert sse_app.state.mcp_server == mock_mcp_server


class TestSSETransportCORS:
    """Tests for CORS configuration."""
    
    def test_cors_allows_all_origins(self, sse_app):
        """Test CORS allows all origins."""
        client = TestClient(sse_app)
        
        # Make a preflight request
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        
        # CORS should allow the request
        assert response.status_code in [200, 204]


