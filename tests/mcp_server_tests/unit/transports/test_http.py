"""
Unit tests for MCP Server HTTP transport
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
def http_app(mock_context, config):
    """Create the HTTP app for testing."""
    from mcp_server.transports.http import create_http_app
    return create_http_app(mock_context, config, enable_auth=False)


class TestHTTPTransportHealth:
    """Tests for health endpoint."""
    
    def test_health_check_healthy(self, http_app, mock_context):
        """Test health check returns healthy status."""
        mock_context.provider_manager.get_active_providers.return_value = [
            MagicMock(id=uuid4(), name="Provider 1")
        ]
        
        client = TestClient(http_app)
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_health_check_no_providers(self, http_app, mock_context):
        """Test health check with no providers."""
        mock_context.provider_manager.get_active_providers.return_value = []
        
        client = TestClient(http_app)
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["providers"] == 0


class TestHTTPTransportProjects:
    """Tests for project endpoints."""
    
    def test_list_projects(self, http_app, mock_context):
        """Test listing projects."""
        mock_context.pm_service.list_projects = AsyncMock(return_value={
            "items": [{"id": "proj1", "name": "Project 1"}],
            "total": 1
        })
        mock_context.pm_service.__aenter__ = AsyncMock(return_value=mock_context.pm_service)
        mock_context.pm_service.__aexit__ = AsyncMock(return_value=None)
        
        client = TestClient(http_app)
        response = client.get("/projects")
        
        assert response.status_code == 200


class TestHTTPTransportTasks:
    """Tests for task endpoints."""
    
    def test_list_my_tasks(self, http_app, mock_context):
        """Test listing my tasks."""
        mock_context.pm_service.list_tasks = AsyncMock(return_value={
            "items": [{"id": "task1", "title": "Task 1"}],
            "total": 1
        })
        mock_context.pm_service.__aenter__ = AsyncMock(return_value=mock_context.pm_service)
        mock_context.pm_service.__aexit__ = AsyncMock(return_value=None)
        
        client = TestClient(http_app)
        response = client.get("/tasks/my")
        
        assert response.status_code == 200


class TestHTTPTransportSprints:
    """Tests for sprint endpoints."""
    
    def test_get_sprint(self, http_app, mock_context):
        """Test getting a sprint."""
        mock_context.pm_service.get_sprint = AsyncMock(return_value={
            "id": "sprint1", "name": "Sprint 1"
        })
        mock_context.pm_service.__aenter__ = AsyncMock(return_value=mock_context.pm_service)
        mock_context.pm_service.__aexit__ = AsyncMock(return_value=None)
        
        client = TestClient(http_app)
        response = client.get("/sprints/sprint1")
        
        assert response.status_code == 200


class TestHTTPTransportUsers:
    """Tests for user endpoints."""
    
    def test_list_users(self, http_app, mock_context):
        """Test listing users."""
        mock_context.pm_service.list_users = AsyncMock(return_value={
            "items": [{"id": "user1", "name": "User 1"}],
            "total": 1
        })
        mock_context.pm_service.__aenter__ = AsyncMock(return_value=mock_context.pm_service)
        mock_context.pm_service.__aexit__ = AsyncMock(return_value=None)
        
        client = TestClient(http_app)
        response = client.get("/users")
        
        assert response.status_code == 200


class TestHTTPTransportTools:
    """Tests for tool endpoints."""
    
    def test_list_tools(self, http_app, mock_context):
        """Test listing tools."""
        client = TestClient(http_app)
        response = client.get("/tools")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


