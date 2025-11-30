"""
Unit tests for Epics V2 tools
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from mcp_server.core.tool_context import ToolContext
from mcp_server.tools.epics_v2.list_epics import ListEpicsTool
from mcp_server.tools.epics_v2.get_epic import GetEpicTool
from mcp_server.tools.epics_v2.create_epic import CreateEpicTool
from mcp_server.tools.epics_v2.update_epic import UpdateEpicTool
from mcp_server.tools.epics_v2.delete_epic import DeleteEpicTool
from mcp_server.tools.epics_v2.link_task_to_epic import LinkTaskToEpicTool
from mcp_server.tools.epics_v2.unlink_task_from_epic import UnlinkTaskFromEpicTool


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
    provider = MagicMock()
    provider.list_epics = AsyncMock(return_value=[])
    provider.get_epic = AsyncMock(return_value=None)
    provider.create_epic = AsyncMock(return_value={})
    provider.update_epic = AsyncMock(return_value={})
    provider.delete_epic = AsyncMock(return_value=None)
    provider.link_task_to_epic = AsyncMock(return_value={})
    provider.unlink_task_from_epic = AsyncMock(return_value={})
    provider.update_task = AsyncMock(return_value={})
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
def sample_epic():
    """Create a sample epic dict."""
    return {
        "id": "epic1",
        "name": "Epic 1",
        "description": "Test epic",
        "status": "open",
        "project_id": "proj1"
    }


@pytest.fixture
def sample_task():
    """Create a sample task dict."""
    return {
        "id": "task1",
        "title": "Task 1",
        "epic_id": None
    }


class TestListEpicsTool:
    """Tests for ListEpicsTool."""
    
    @pytest.mark.asyncio
    async def test_list_epics_success(self, mock_context, mock_provider, mock_provider_conn, sample_epic):
        """Test listing epics successfully."""
        provider_id = str(mock_provider_conn.id)
        project_id = f"{provider_id}:proj1"
        
        mock_context.provider_manager.get_provider = AsyncMock(return_value=mock_provider)
        mock_context.provider_manager.get_provider_by_id.return_value = mock_provider_conn
        mock_provider.list_epics = AsyncMock(return_value=[sample_epic])
        
        tool = ListEpicsTool(mock_context)
        result = await tool.execute(project_id=project_id)
        
        assert "epics" in result
        assert len(result["epics"]) == 1


class TestGetEpicTool:
    """Tests for GetEpicTool."""
    
    @pytest.mark.asyncio
    async def test_get_epic_success(self, mock_context, mock_provider, mock_provider_conn, sample_epic):
        """Test getting an epic successfully."""
        epic_id = "epic1"
        
        mock_context.provider_manager.get_provider = AsyncMock(return_value=mock_provider)
        mock_context.provider_manager.get_active_providers.return_value = [mock_provider_conn]
        mock_context.provider_manager.create_provider_instance.return_value = mock_provider
        mock_provider.get_epic = AsyncMock(return_value=sample_epic)
        
        tool = GetEpicTool(mock_context)
        result = await tool.execute(epic_id=epic_id)
        
        assert result["name"] == "Epic 1"


class TestCreateEpicTool:
    """Tests for CreateEpicTool."""
    
    @pytest.mark.asyncio
    async def test_create_epic_success(self, mock_context, mock_provider, mock_provider_conn, sample_epic):
        """Test creating an epic successfully."""
        provider_id = str(mock_provider_conn.id)
        project_id = f"{provider_id}:proj1"
        
        mock_context.provider_manager.get_provider = AsyncMock(return_value=mock_provider)
        mock_context.provider_manager.get_provider_by_id.return_value = mock_provider_conn
        mock_provider.create_epic = AsyncMock(return_value=sample_epic)
        
        tool = CreateEpicTool(mock_context)
        result = await tool.execute(project_id=project_id, name="Epic 1")
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_create_epic_not_supported(self, mock_context, mock_provider, mock_provider_conn):
        """Test create when provider doesn't support it."""
        provider_id = str(mock_provider_conn.id)
        project_id = f"{provider_id}:proj1"
        
        mock_context.provider_manager.get_provider = AsyncMock(return_value=mock_provider)
        mock_context.provider_manager.get_provider_by_id.return_value = mock_provider_conn
        del mock_provider.create_epic
        
        tool = CreateEpicTool(mock_context)
        result = await tool.execute(project_id=project_id, name="Epic 1")
        
        assert result["success"] is False
        assert "not supported" in result["message"]


class TestUpdateEpicTool:
    """Tests for UpdateEpicTool."""
    
    @pytest.mark.asyncio
    async def test_update_epic_success(self, mock_context, mock_provider, mock_provider_conn, sample_epic):
        """Test updating an epic successfully."""
        provider_id = str(mock_provider_conn.id)
        epic_id = f"{provider_id}:epic1"
        
        mock_context.provider_manager.get_provider = AsyncMock(return_value=mock_provider)
        mock_context.provider_manager.get_provider_by_id.return_value = mock_provider_conn
        mock_provider.update_epic = AsyncMock(return_value={**sample_epic, "name": "Updated Epic"})
        
        tool = UpdateEpicTool(mock_context)
        result = await tool.execute(epic_id=epic_id, name="Updated Epic")
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_update_epic_no_fields(self, mock_context):
        """Test update with no fields to update."""
        tool = UpdateEpicTool(mock_context)
        result = await tool.execute(epic_id="test:epic1")
        
        assert result["success"] is False
        assert "At least one field" in result["message"]


class TestDeleteEpicTool:
    """Tests for DeleteEpicTool."""
    
    @pytest.mark.asyncio
    async def test_delete_epic_success(self, mock_context, mock_provider, mock_provider_conn):
        """Test deleting an epic successfully."""
        provider_id = str(mock_provider_conn.id)
        epic_id = f"{provider_id}:epic1"
        
        mock_context.provider_manager.get_provider = AsyncMock(return_value=mock_provider)
        mock_context.provider_manager.get_provider_by_id.return_value = mock_provider_conn
        mock_provider.delete_epic = AsyncMock()
        
        tool = DeleteEpicTool(mock_context)
        result = await tool.execute(epic_id=epic_id)
        
        assert result["success"] is True


class TestLinkTaskToEpicTool:
    """Tests for LinkTaskToEpicTool."""
    
    @pytest.mark.asyncio
    async def test_link_task_success(self, mock_context, mock_provider, mock_provider_conn, sample_task):
        """Test linking a task to an epic successfully."""
        provider_id = str(mock_provider_conn.id)
        task_id = f"{provider_id}:task1"
        
        mock_context.provider_manager.get_provider = AsyncMock(return_value=mock_provider)
        mock_context.provider_manager.get_provider_by_id.return_value = mock_provider_conn
        mock_provider.link_task_to_epic = AsyncMock(return_value={**sample_task, "epic_id": "epic1"})
        
        tool = LinkTaskToEpicTool(mock_context)
        result = await tool.execute(task_id=task_id, epic_id="epic1")
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_link_task_via_update(self, mock_context, mock_provider, mock_provider_conn, sample_task):
        """Test linking a task via update_task fallback."""
        provider_id = str(mock_provider_conn.id)
        task_id = f"{provider_id}:task1"
        
        mock_context.provider_manager.get_provider = AsyncMock(return_value=mock_provider)
        mock_context.provider_manager.get_provider_by_id.return_value = mock_provider_conn
        del mock_provider.link_task_to_epic  # Remove direct method
        mock_provider.update_task = AsyncMock(return_value={**sample_task, "epic_id": "epic1"})
        
        tool = LinkTaskToEpicTool(mock_context)
        result = await tool.execute(task_id=task_id, epic_id="epic1")
        
        assert result["success"] is True


class TestUnlinkTaskFromEpicTool:
    """Tests for UnlinkTaskFromEpicTool."""
    
    @pytest.mark.asyncio
    async def test_unlink_task_success(self, mock_context, mock_provider, mock_provider_conn, sample_task):
        """Test unlinking a task from an epic successfully."""
        provider_id = str(mock_provider_conn.id)
        task_id = f"{provider_id}:task1"
        
        mock_context.provider_manager.get_provider = AsyncMock(return_value=mock_provider)
        mock_context.provider_manager.get_provider_by_id.return_value = mock_provider_conn
        mock_provider.unlink_task_from_epic = AsyncMock(return_value=sample_task)
        
        tool = UnlinkTaskFromEpicTool(mock_context)
        result = await tool.execute(task_id=task_id)
        
        assert result["success"] is True

