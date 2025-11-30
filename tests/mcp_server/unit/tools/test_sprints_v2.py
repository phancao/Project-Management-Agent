"""
Unit tests for Sprints V2 tools
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from mcp_server.core.tool_context import ToolContext
from mcp_server.tools.sprints_v2.list_sprints import ListSprintsTool
from mcp_server.tools.sprints_v2.get_sprint import GetSprintTool
from mcp_server.tools.sprints_v2.create_sprint import CreateSprintTool
from mcp_server.tools.sprints_v2.update_sprint import UpdateSprintTool
from mcp_server.tools.sprints_v2.delete_sprint import DeleteSprintTool
from mcp_server.tools.sprints_v2.start_sprint import StartSprintTool
from mcp_server.tools.sprints_v2.complete_sprint import CompleteSprintTool
from mcp_server.tools.sprints_v2.get_sprint_tasks import GetSprintTasksTool


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
    context.pm_service = AsyncMock()
    context.user_id = str(uuid4())
    return context


@pytest.fixture
def mock_provider():
    """Create a mock provider instance."""
    provider = MagicMock()
    provider.list_sprints = AsyncMock(return_value=[])
    provider.get_sprint = AsyncMock(return_value=None)
    provider.create_sprint = AsyncMock(return_value={})
    provider.update_sprint = AsyncMock(return_value={})
    provider.delete_sprint = AsyncMock(return_value=None)
    provider.start_sprint = AsyncMock(return_value={})
    provider.complete_sprint = AsyncMock(return_value={})
    provider.list_tasks = AsyncMock(return_value=[])
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
def sample_sprint():
    """Create a sample sprint dict."""
    return {
        "id": "sprint1",
        "name": "Sprint 1",
        "status": "active",
        "start_date": "2024-01-01",
        "end_date": "2024-01-14",
        "project_id": "proj1"
    }


class TestListSprintsTool:
    """Tests for ListSprintsTool."""
    
    @pytest.mark.asyncio
    async def test_list_sprints_success(self, mock_context, sample_sprint):
        """Test listing sprints successfully."""
        mock_context.pm_service.list_sprints = AsyncMock(return_value={
            "items": [sample_sprint],
            "total": 1
        })
        
        tool = ListSprintsTool(mock_context)
        result = await tool.execute(project_id="test:proj1")
        
        assert "sprints" in result
        assert result["total"] == 1


class TestGetSprintTool:
    """Tests for GetSprintTool."""
    
    @pytest.mark.asyncio
    async def test_get_sprint_success(self, mock_context, mock_provider, mock_provider_conn, sample_sprint):
        """Test getting a sprint successfully."""
        provider_id = str(mock_provider_conn.id)
        sprint_id = f"{provider_id}:sprint1"
        
        mock_context.provider_manager.get_provider = AsyncMock(return_value=mock_provider)
        mock_provider.get_sprint = AsyncMock(return_value=sample_sprint)
        
        tool = GetSprintTool(mock_context)
        result = await tool.execute(sprint_id=sprint_id)
        
        assert result["name"] == "Sprint 1"


class TestCreateSprintTool:
    """Tests for CreateSprintTool."""
    
    @pytest.mark.asyncio
    async def test_create_sprint_success(self, mock_context, mock_provider, mock_provider_conn, sample_sprint):
        """Test creating a sprint successfully."""
        provider_id = str(mock_provider_conn.id)
        project_id = f"{provider_id}:proj1"
        
        mock_context.provider_manager.get_provider = AsyncMock(return_value=mock_provider)
        mock_context.provider_manager.get_provider_by_id.return_value = mock_provider_conn
        mock_provider.create_sprint = AsyncMock(return_value=sample_sprint)
        
        tool = CreateSprintTool(mock_context)
        result = await tool.execute(
            project_id=project_id,
            name="Sprint 1",
            start_date="2024-01-01",
            end_date="2024-01-14"
        )
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_create_sprint_not_supported(self, mock_context, mock_provider, mock_provider_conn):
        """Test create when provider doesn't support it."""
        provider_id = str(mock_provider_conn.id)
        project_id = f"{provider_id}:proj1"
        
        mock_context.provider_manager.get_provider = AsyncMock(return_value=mock_provider)
        mock_context.provider_manager.get_provider_by_id.return_value = mock_provider_conn
        del mock_provider.create_sprint
        
        tool = CreateSprintTool(mock_context)
        result = await tool.execute(
            project_id=project_id,
            name="Sprint 1",
            start_date="2024-01-01",
            end_date="2024-01-14"
        )
        
        assert result["success"] is False
        assert "not supported" in result["message"]


class TestUpdateSprintTool:
    """Tests for UpdateSprintTool."""
    
    @pytest.mark.asyncio
    async def test_update_sprint_success(self, mock_context, mock_provider, mock_provider_conn, sample_sprint):
        """Test updating a sprint successfully."""
        provider_id = str(mock_provider_conn.id)
        sprint_id = f"{provider_id}:sprint1"
        
        mock_context.provider_manager.get_provider = AsyncMock(return_value=mock_provider)
        mock_context.provider_manager.get_provider_by_id.return_value = mock_provider_conn
        mock_provider.update_sprint = AsyncMock(return_value={**sample_sprint, "name": "Updated Sprint"})
        
        tool = UpdateSprintTool(mock_context)
        result = await tool.execute(sprint_id=sprint_id, name="Updated Sprint")
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_update_sprint_no_fields(self, mock_context):
        """Test update with no fields to update."""
        tool = UpdateSprintTool(mock_context)
        result = await tool.execute(sprint_id="test:sprint1")
        
        assert result["success"] is False
        assert "At least one field" in result["message"]


class TestDeleteSprintTool:
    """Tests for DeleteSprintTool."""
    
    @pytest.mark.asyncio
    async def test_delete_sprint_success(self, mock_context, mock_provider, mock_provider_conn):
        """Test deleting a sprint successfully."""
        provider_id = str(mock_provider_conn.id)
        sprint_id = f"{provider_id}:sprint1"
        
        mock_context.provider_manager.get_provider = AsyncMock(return_value=mock_provider)
        mock_context.provider_manager.get_provider_by_id.return_value = mock_provider_conn
        mock_provider.delete_sprint = AsyncMock()
        
        tool = DeleteSprintTool(mock_context)
        result = await tool.execute(sprint_id=sprint_id)
        
        assert result["success"] is True


class TestStartSprintTool:
    """Tests for StartSprintTool."""
    
    @pytest.mark.asyncio
    async def test_start_sprint_success(self, mock_context, mock_provider, mock_provider_conn, sample_sprint):
        """Test starting a sprint successfully."""
        provider_id = str(mock_provider_conn.id)
        sprint_id = f"{provider_id}:sprint1"
        
        mock_context.provider_manager.get_provider = AsyncMock(return_value=mock_provider)
        mock_context.provider_manager.get_provider_by_id.return_value = mock_provider_conn
        mock_provider.start_sprint = AsyncMock(return_value={**sample_sprint, "status": "active"})
        
        tool = StartSprintTool(mock_context)
        result = await tool.execute(sprint_id=sprint_id)
        
        assert result["success"] is True


class TestCompleteSprintTool:
    """Tests for CompleteSprintTool."""
    
    @pytest.mark.asyncio
    async def test_complete_sprint_success(self, mock_context, mock_provider, mock_provider_conn, sample_sprint):
        """Test completing a sprint successfully."""
        provider_id = str(mock_provider_conn.id)
        sprint_id = f"{provider_id}:sprint1"
        
        mock_context.provider_manager.get_provider = AsyncMock(return_value=mock_provider)
        mock_context.provider_manager.get_provider_by_id.return_value = mock_provider_conn
        mock_provider.complete_sprint = AsyncMock(return_value={**sample_sprint, "status": "closed"})
        
        tool = CompleteSprintTool(mock_context)
        result = await tool.execute(sprint_id=sprint_id)
        
        assert result["success"] is True


class TestGetSprintTasksTool:
    """Tests for GetSprintTasksTool."""
    
    @pytest.mark.asyncio
    async def test_get_sprint_tasks_success(self, mock_context, mock_provider, mock_provider_conn, sample_sprint):
        """Test getting sprint tasks successfully."""
        provider_id = str(mock_provider_conn.id)
        sprint_id = f"{provider_id}:sprint1"
        
        tasks = [
            {"id": "1", "title": "Task 1", "sprint_id": "sprint1"},
            {"id": "2", "title": "Task 2", "sprint_id": "sprint1"},
        ]
        
        mock_context.provider_manager.get_provider = AsyncMock(return_value=mock_provider)
        mock_context.provider_manager.get_provider_by_id.return_value = mock_provider_conn
        mock_context.provider_manager.get_active_providers.return_value = [mock_provider_conn]
        mock_provider.get_sprint = AsyncMock(return_value=sample_sprint)
        mock_provider.get_sprint_tasks = AsyncMock(return_value=tasks)
        mock_provider.list_tasks = AsyncMock(return_value=tasks)
        
        tool = GetSprintTasksTool(mock_context)
        result = await tool.execute(sprint_id=sprint_id)
        
        assert "tasks" in result
        assert result["sprint_id"] == sprint_id

