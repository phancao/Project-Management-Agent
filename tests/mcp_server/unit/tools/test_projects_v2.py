"""
Unit tests for Projects V2 tools
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from mcp_server.core.tool_context import ToolContext
from mcp_server.tools.projects_v2.list_projects import ListProjectsTool
from mcp_server.tools.projects_v2.get_project import GetProjectTool
from mcp_server.tools.projects_v2.create_project import CreateProjectTool
from mcp_server.tools.projects_v2.update_project import UpdateProjectTool
from mcp_server.tools.projects_v2.delete_project import DeleteProjectTool
from mcp_server.tools.projects_v2.search_projects import SearchProjectsTool


@pytest.fixture
def mock_context():
    """Create a mock ToolContext."""
    context = MagicMock(spec=ToolContext)
    context.provider_manager = MagicMock()
    context.provider_manager.get_provider = AsyncMock()
    context.provider_manager.get_provider_by_id = MagicMock()
    context.provider_manager.get_active_providers = MagicMock(return_value=[])
    context.provider_manager.create_provider_instance = MagicMock()
    context.provider_manager.record_error = MagicMock()
    context.pm_service = MagicMock()
    context.user_id = str(uuid4())
    return context


@pytest.fixture
def mock_provider():
    """Create a mock provider instance."""
    provider = AsyncMock()
    provider.list_projects = AsyncMock(return_value=[])
    provider.get_project = AsyncMock(return_value=None)
    provider.create_project = AsyncMock(return_value={})
    provider.update_project = AsyncMock(return_value={})
    provider.delete_project = AsyncMock(return_value=None)
    return provider


@pytest.fixture
def mock_provider_conn():
    """Create a mock provider connection."""
    conn = MagicMock()
    conn.id = uuid4()
    conn.name = "Test Provider"
    conn.provider_type = "openproject"
    return conn


@pytest.fixture
def sample_project():
    """Create a sample project dict."""
    return {
        "id": "proj1",
        "name": "Test Project",
        "description": "Test description",
        "status": "active"
    }


class TestListProjectsTool:
    """Tests for ListProjectsTool."""
    
    @pytest.mark.asyncio
    async def test_list_projects_success(self, mock_context, mock_provider, mock_provider_conn, sample_project):
        """Test listing projects successfully."""
        mock_context.provider_manager.get_active_providers.return_value = [mock_provider_conn]
        mock_context.provider_manager.create_provider_instance.return_value = mock_provider
        mock_provider.list_projects.return_value = [sample_project]
        
        tool = ListProjectsTool(mock_context)
        result = await tool.execute()
        
        assert "projects" in result
        assert len(result["projects"]) == 1
        mock_provider.list_projects.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_projects_no_providers(self, mock_context):
        """Test listing projects with no providers."""
        mock_context.provider_manager.get_active_providers.return_value = []
        
        tool = ListProjectsTool(mock_context)
        result = await tool.execute()
        
        assert result["projects"] == []
        assert result["total"] == 0


class TestGetProjectTool:
    """Tests for GetProjectTool."""
    
    @pytest.mark.asyncio
    async def test_get_project_success(self, mock_context, mock_provider, mock_provider_conn, sample_project):
        """Test getting a project successfully."""
        provider_id = str(mock_provider_conn.id)
        project_id = f"{provider_id}:proj1"
        
        mock_context.provider_manager.get_provider = AsyncMock(return_value=mock_provider)
        mock_context.provider_manager.get_provider_by_id.return_value = mock_provider_conn
        mock_context.provider_manager.get_active_providers.return_value = [mock_provider_conn]
        mock_provider.get_project = AsyncMock(return_value=sample_project)
        
        tool = GetProjectTool(mock_context)
        result = await tool.execute(project_id=project_id)
        
        assert result is not None
        mock_provider.get_project.assert_called_once_with("proj1")


class TestCreateProjectTool:
    """Tests for CreateProjectTool."""
    
    @pytest.mark.asyncio
    async def test_create_project_success(self, mock_context, mock_provider, mock_provider_conn, sample_project):
        """Test creating a project successfully."""
        mock_context.provider_manager.get_active_providers.return_value = [mock_provider_conn]
        mock_context.provider_manager.create_provider_instance.return_value = mock_provider
        mock_provider.create_project.return_value = sample_project
        
        tool = CreateProjectTool(mock_context)
        result = await tool.execute(name="New Project", description="New description")
        
        assert result["success"] is True
        mock_provider.create_project.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_project_not_supported(self, mock_context, mock_provider, mock_provider_conn):
        """Test create when provider doesn't support it."""
        mock_context.provider_manager.get_active_providers.return_value = [mock_provider_conn]
        mock_context.provider_manager.create_provider_instance.return_value = mock_provider
        del mock_provider.create_project  # Remove the method
        
        tool = CreateProjectTool(mock_context)
        result = await tool.execute(name="New Project")
        
        assert result["success"] is False
        assert "not supported" in result["message"]


class TestUpdateProjectTool:
    """Tests for UpdateProjectTool."""
    
    @pytest.mark.asyncio
    async def test_update_project_success(self, mock_context, mock_provider, mock_provider_conn, sample_project):
        """Test updating a project successfully."""
        provider_id = str(mock_provider_conn.id)
        project_id = f"{provider_id}:proj1"
        
        mock_context.provider_manager.get_provider = AsyncMock(return_value=mock_provider)
        mock_context.provider_manager.get_provider_by_id.return_value = mock_provider_conn
        mock_provider.update_project = AsyncMock(return_value={**sample_project, "name": "Updated Project"})
        
        tool = UpdateProjectTool(mock_context)
        result = await tool.execute(project_id=project_id, name="Updated Project")
        
        assert result["success"] is True
        mock_provider.update_project.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_project_no_fields(self, mock_context):
        """Test update with no fields to update."""
        tool = UpdateProjectTool(mock_context)
        result = await tool.execute(project_id="test:proj1")
        
        assert result["success"] is False
        assert "At least one field" in result["message"]


class TestDeleteProjectTool:
    """Tests for DeleteProjectTool."""
    
    @pytest.mark.asyncio
    async def test_delete_project_success(self, mock_context, mock_provider, mock_provider_conn):
        """Test deleting a project successfully."""
        provider_id = str(mock_provider_conn.id)
        project_id = f"{provider_id}:proj1"
        
        mock_context.provider_manager.get_provider = AsyncMock(return_value=mock_provider)
        mock_context.provider_manager.get_provider_by_id.return_value = mock_provider_conn
        mock_provider.delete_project = AsyncMock()
        
        tool = DeleteProjectTool(mock_context)
        result = await tool.execute(project_id=project_id)
        
        assert result["success"] is True
        mock_provider.delete_project.assert_called_once_with("proj1")


class TestSearchProjectsTool:
    """Tests for SearchProjectsTool."""
    
    @pytest.mark.asyncio
    async def test_search_projects_success(self, mock_context, mock_provider, mock_provider_conn):
        """Test searching projects successfully."""
        projects = [
            {"id": "1", "name": "API Project", "description": ""},
            {"id": "2", "name": "Web App", "description": "API integration"},
            {"id": "3", "name": "Mobile App", "description": ""},
        ]
        
        mock_context.provider_manager.get_active_providers.return_value = [mock_provider_conn]
        mock_context.provider_manager.create_provider_instance.return_value = mock_provider
        mock_provider.list_projects.return_value = projects
        
        tool = SearchProjectsTool(mock_context)
        result = await tool.execute(query="api")
        
        assert len(result["projects"]) == 2  # "API Project" and "API integration"
        assert result["query"] == "api"


