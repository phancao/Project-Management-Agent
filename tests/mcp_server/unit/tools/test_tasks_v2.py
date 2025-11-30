"""
Unit tests for Tasks V2 tools
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from mcp_server.core.tool_context import ToolContext
from mcp_server.tools.tasks_v2.list_tasks import ListTasksTool
from mcp_server.tools.tasks_v2.get_task import GetTaskTool
from mcp_server.tools.tasks_v2.create_task import CreateTaskTool
from mcp_server.tools.tasks_v2.update_task import UpdateTaskTool
from mcp_server.tools.tasks_v2.delete_task import DeleteTaskTool
from mcp_server.tools.tasks_v2.assign_task import AssignTaskTool
from mcp_server.tools.tasks_v2.update_task_status import UpdateTaskStatusTool
from mcp_server.tools.tasks_v2.search_tasks import SearchTasksTool


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
    provider.list_tasks = AsyncMock(return_value=[])
    provider.get_task = AsyncMock(return_value=None)
    provider.create_task = AsyncMock(return_value={})
    provider.update_task = AsyncMock(return_value={})
    provider.delete_task = AsyncMock(return_value=None)
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
def sample_task():
    """Create a sample task dict."""
    return {
        "id": "123",
        "title": "Test Task",
        "description": "Test description",
        "status": "open",
        "assignee_id": "user1",
        "project_id": "proj1",
        "sprint_id": None,
        "story_points": 5
    }


class TestListTasksTool:
    """Tests for ListTasksTool."""
    
    @pytest.mark.asyncio
    async def test_list_tasks_no_filters(self, mock_context, mock_provider, mock_provider_conn, sample_task):
        """Test listing tasks without filters."""
        mock_context.provider_manager.get_active_providers.return_value = [mock_provider_conn]
        mock_context.provider_manager.create_provider_instance.return_value = mock_provider
        mock_provider.list_tasks.return_value = [sample_task]
        
        tool = ListTasksTool(mock_context)
        result = await tool.execute()
        
        assert "tasks" in result
        assert "total" in result
        mock_provider.list_tasks.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_tasks_with_project_filter(self, mock_context, mock_provider, mock_provider_conn, sample_task):
        """Test listing tasks with project filter."""
        provider_id = str(mock_provider_conn.id)
        project_id = f"{provider_id}:proj1"
        
        mock_context.provider_manager.get_provider = AsyncMock(return_value=mock_provider)
        mock_context.provider_manager.get_provider_by_id.return_value = mock_provider_conn
        mock_provider.list_tasks.return_value = [sample_task]
        
        tool = ListTasksTool(mock_context)
        result = await tool.execute(project_id=project_id)
        
        assert "tasks" in result
        mock_provider.list_tasks.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_tasks_with_limit(self, mock_context, mock_provider, mock_provider_conn):
        """Test listing tasks with limit."""
        tasks = [{"id": str(i), "title": f"Task {i}"} for i in range(10)]
        mock_context.provider_manager.get_active_providers.return_value = [mock_provider_conn]
        mock_context.provider_manager.create_provider_instance.return_value = mock_provider
        mock_provider.list_tasks.return_value = tasks
        
        tool = ListTasksTool(mock_context)
        result = await tool.execute(limit=5)
        
        assert len(result["tasks"]) == 5
        assert result["total"] == 10


class TestGetTaskTool:
    """Tests for GetTaskTool."""
    
    @pytest.mark.asyncio
    async def test_get_task_success(self, mock_context, mock_provider, mock_provider_conn, sample_task):
        """Test getting a task successfully."""
        provider_id = str(mock_provider_conn.id)
        task_id = "123"  # Use simple task ID
        project_id = f"{provider_id}:proj1"
        
        mock_context.provider_manager.get_provider = AsyncMock(return_value=mock_provider)
        mock_context.provider_manager.get_active_providers.return_value = [mock_provider_conn]
        mock_context.provider_manager.create_provider_instance.return_value = mock_provider
        mock_provider.get_task = AsyncMock(return_value=sample_task)
        
        tool = GetTaskTool(mock_context)
        result = await tool.execute(task_id=task_id, project_id=project_id)
        
        assert result["title"] == "Test Task"


class TestCreateTaskTool:
    """Tests for CreateTaskTool."""
    
    @pytest.mark.asyncio
    async def test_create_task_success(self, mock_context, mock_provider, mock_provider_conn, sample_task):
        """Test creating a task successfully."""
        provider_id = str(mock_provider_conn.id)
        project_id = f"{provider_id}:proj1"
        
        mock_context.provider_manager.get_provider = AsyncMock(return_value=mock_provider)
        mock_provider.create_task = AsyncMock(return_value=sample_task)
        
        tool = CreateTaskTool(mock_context)
        result = await tool.execute(
            project_id=project_id,
            title="New Task",
            description="New description"
        )
        
        mock_provider.create_task.assert_called_once()


class TestUpdateTaskTool:
    """Tests for UpdateTaskTool."""
    
    @pytest.mark.asyncio
    async def test_update_task_success(self, mock_context, mock_provider, mock_provider_conn, sample_task):
        """Test updating a task successfully."""
        provider_id = str(mock_provider_conn.id)
        task_id = "123"  # Use simple task ID
        
        mock_context.provider_manager.get_provider = AsyncMock(return_value=mock_provider)
        mock_context.provider_manager.get_active_providers.return_value = [mock_provider_conn]
        mock_context.provider_manager.create_provider_instance.return_value = mock_provider
        mock_provider.update_task = AsyncMock(return_value={**sample_task, "title": "Updated Task"})
        
        tool = UpdateTaskTool(mock_context)
        result = await tool.execute(task_id=task_id, title="Updated Task")
        
        mock_provider.update_task.assert_called_once()


class TestDeleteTaskTool:
    """Tests for DeleteTaskTool."""
    
    @pytest.mark.asyncio
    async def test_delete_task_success(self, mock_context, mock_provider, mock_provider_conn):
        """Test deleting a task successfully."""
        provider_id = str(mock_provider_conn.id)
        task_id = f"{provider_id}:123"
        
        mock_context.provider_manager.get_provider = AsyncMock(return_value=mock_provider)
        mock_provider.delete_task = AsyncMock()
        
        tool = DeleteTaskTool(mock_context)
        result = await tool.execute(task_id=task_id)
        
        assert result["success"] is True
        mock_provider.delete_task.assert_called_once_with("123")
    
    @pytest.mark.asyncio
    async def test_delete_task_not_supported(self, mock_context, mock_provider, mock_provider_conn):
        """Test delete when provider doesn't support it."""
        provider_id = str(mock_provider_conn.id)
        task_id = f"{provider_id}:123"
        
        mock_context.provider_manager.get_provider = AsyncMock(return_value=mock_provider)
        del mock_provider.delete_task  # Remove the method
        
        tool = DeleteTaskTool(mock_context)
        result = await tool.execute(task_id=task_id)
        
        assert result["success"] is False
        assert "not supported" in result["message"]


class TestAssignTaskTool:
    """Tests for AssignTaskTool."""
    
    @pytest.mark.asyncio
    async def test_assign_task_success(self, mock_context, mock_provider, mock_provider_conn, sample_task):
        """Test assigning a task successfully."""
        provider_id = str(mock_provider_conn.id)
        task_id = f"{provider_id}:123"
        
        mock_context.provider_manager.get_provider = AsyncMock(return_value=mock_provider)
        mock_provider.update_task = AsyncMock(return_value={**sample_task, "assignee_id": "user2"})
        
        tool = AssignTaskTool(mock_context)
        result = await tool.execute(task_id=task_id, assignee_id="user2")
        
        assert result["success"] is True
        mock_provider.update_task.assert_called_once()


class TestUpdateTaskStatusTool:
    """Tests for UpdateTaskStatusTool."""
    
    @pytest.mark.asyncio
    async def test_update_status_success(self, mock_context, mock_provider, mock_provider_conn, sample_task):
        """Test updating task status successfully."""
        provider_id = str(mock_provider_conn.id)
        task_id = f"{provider_id}:123"
        
        mock_context.provider_manager.get_provider = AsyncMock(return_value=mock_provider)
        mock_provider.update_task = AsyncMock(return_value={**sample_task, "status": "done"})
        
        tool = UpdateTaskStatusTool(mock_context)
        result = await tool.execute(task_id=task_id, status="done")
        
        assert result["success"] is True
        mock_provider.update_task.assert_called_once()


class TestSearchTasksTool:
    """Tests for SearchTasksTool."""
    
    @pytest.mark.asyncio
    async def test_search_tasks_success(self, mock_context, mock_provider, mock_provider_conn):
        """Test searching tasks successfully."""
        tasks = [
            {"id": "1", "title": "Fix bug in login", "description": ""},
            {"id": "2", "title": "Add feature", "description": "New login feature"},
            {"id": "3", "title": "Update docs", "description": ""},
        ]
        
        mock_context.provider_manager.get_active_providers.return_value = [mock_provider_conn]
        mock_context.provider_manager.create_provider_instance.return_value = mock_provider
        mock_provider.list_tasks.return_value = tasks
        
        tool = SearchTasksTool(mock_context)
        result = await tool.execute(query="login")
        
        assert len(result["tasks"]) == 2  # "Fix bug in login" and "New login feature"
        assert result["query"] == "login"


