"""
Unit tests for Backend PMServiceHandler
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.server.pm_service_client import PMServiceHandler, get_pm_service_handler


@pytest.fixture
def mock_client():
    """Create a mock AsyncPMServiceClient."""
    client = AsyncMock()
    client.list_projects = AsyncMock(return_value={"items": [], "total": 0})
    client.get_project = AsyncMock(return_value=None)
    client.list_tasks = AsyncMock(return_value={"items": [], "total": 0})
    client.get_task = AsyncMock(return_value=None)
    client.create_task = AsyncMock(return_value={})
    client.update_task = AsyncMock(return_value={})
    client.list_sprints = AsyncMock(return_value={"items": [], "total": 0})
    client.get_sprint = AsyncMock(return_value=None)
    client.list_users = AsyncMock(return_value={"items": [], "total": 0})
    client.get_user = AsyncMock(return_value=None)
    client.list_providers = AsyncMock(return_value={"items": [], "total": 0})
    client.sync_provider = AsyncMock(return_value={})
    return client


@pytest.fixture
def handler():
    """Create a PMServiceHandler instance."""
    return PMServiceHandler(user_id="test-user")


class TestPMServiceHandlerInit:
    """Tests for handler initialization."""
    
    def test_init_with_user_id(self):
        """Test initialization with user ID."""
        handler = PMServiceHandler(user_id="user123")
        assert handler.user_id == "user123"
        assert handler._client is not None
    
    def test_init_without_user_id(self):
        """Test initialization without user ID."""
        handler = PMServiceHandler()
        assert handler.user_id is None
    
    def test_from_db_session(self):
        """Test creating handler from db session (compatibility)."""
        handler = PMServiceHandler.from_db_session(
            db_session=MagicMock(),
            user_id="user123"
        )
        assert handler.user_id == "user123"


class TestPMServiceHandlerProjects:
    """Tests for project operations."""
    
    @pytest.mark.asyncio
    async def test_list_all_projects(self, handler, mock_client):
        """Test listing all projects."""
        mock_client.list_projects.return_value = {
            "items": [{"id": "proj1", "name": "Project 1"}],
            "total": 1
        }
        
        with patch.object(handler, '_client', mock_client):
            # Patch the context manager
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            
            result = await handler.list_all_projects()
            
            assert len(result) == 1
            assert result[0]["name"] == "Project 1"
    
    @pytest.mark.asyncio
    async def test_get_project_success(self, handler, mock_client):
        """Test getting a project successfully."""
        mock_client.get_project.return_value = {"id": "proj1", "name": "Project 1"}
        
        with patch.object(handler, '_client', mock_client):
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            
            result = await handler.get_project("proj1")
            
            assert result["name"] == "Project 1"
    
    @pytest.mark.asyncio
    async def test_get_project_error(self, handler, mock_client):
        """Test getting a project with error."""
        mock_client.get_project.side_effect = Exception("Not found")
        
        with patch.object(handler, '_client', mock_client):
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            
            result = await handler.get_project("nonexistent")
            
            assert result is None


class TestPMServiceHandlerTasks:
    """Tests for task operations."""
    
    @pytest.mark.asyncio
    async def test_list_project_tasks(self, handler, mock_client):
        """Test listing project tasks."""
        mock_client.list_tasks.return_value = {
            "items": [{"id": "task1", "title": "Task 1"}],
            "total": 1
        }
        
        with patch.object(handler, '_client', mock_client):
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            
            result = await handler.list_project_tasks(
                project_id="proj1",
                sprint_id="sprint1",
                status="open"
            )
            
            assert len(result) == 1
            assert result[0]["title"] == "Task 1"
    
    @pytest.mark.asyncio
    async def test_get_task_success(self, handler, mock_client):
        """Test getting a task successfully."""
        mock_client.get_task.return_value = {"id": "task1", "title": "Task 1"}
        
        with patch.object(handler, '_client', mock_client):
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            
            result = await handler.get_task("task1")
            
            assert result["title"] == "Task 1"
    
    @pytest.mark.asyncio
    async def test_create_project_task(self, handler, mock_client):
        """Test creating a task."""
        mock_client.create_task.return_value = {
            "id": "task1",
            "title": "New Task"
        }
        
        with patch.object(handler, '_client', mock_client):
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            
            result = await handler.create_project_task(
                project_id="proj1",
                title="New Task",
                description="Description",
                story_points=5
            )
            
            assert result["title"] == "New Task"
    
    @pytest.mark.asyncio
    async def test_update_task_success(self, handler, mock_client):
        """Test updating a task successfully."""
        mock_client.update_task.return_value = {
            "id": "task1",
            "title": "Updated Task"
        }
        
        with patch.object(handler, '_client', mock_client):
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            
            result = await handler.update_task(
                task_id="task1",
                title="Updated Task"
            )
            
            assert result["title"] == "Updated Task"
    
    @pytest.mark.asyncio
    async def test_update_task_error(self, handler, mock_client):
        """Test updating a task with error."""
        mock_client.update_task.side_effect = Exception("Update failed")
        
        with patch.object(handler, '_client', mock_client):
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            
            result = await handler.update_task(
                task_id="task1",
                title="Updated Task"
            )
            
            assert result is None


class TestPMServiceHandlerSprints:
    """Tests for sprint operations."""
    
    @pytest.mark.asyncio
    async def test_list_project_sprints(self, handler, mock_client):
        """Test listing project sprints."""
        mock_client.list_sprints.return_value = {
            "items": [{"id": "sprint1", "name": "Sprint 1"}],
            "total": 1
        }
        
        with patch.object(handler, '_client', mock_client):
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            
            result = await handler.list_project_sprints(
                project_id="proj1",
                status="active"
            )
            
            assert len(result) == 1
            assert result[0]["name"] == "Sprint 1"
    
    @pytest.mark.asyncio
    async def test_get_sprint_success(self, handler, mock_client):
        """Test getting a sprint successfully."""
        mock_client.get_sprint.return_value = {"id": "sprint1", "name": "Sprint 1"}
        
        with patch.object(handler, '_client', mock_client):
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            
            result = await handler.get_sprint("sprint1")
            
            assert result["name"] == "Sprint 1"


class TestPMServiceHandlerUsers:
    """Tests for user operations."""
    
    @pytest.mark.asyncio
    async def test_list_project_users(self, handler, mock_client):
        """Test listing project users."""
        mock_client.list_users.return_value = {
            "items": [{"id": "user1", "name": "User 1"}],
            "total": 1
        }
        
        with patch.object(handler, '_client', mock_client):
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            
            result = await handler.list_project_users(project_id="proj1")
            
            assert len(result) == 1
            assert result[0]["name"] == "User 1"
    
    @pytest.mark.asyncio
    async def test_get_user_success(self, handler, mock_client):
        """Test getting a user successfully."""
        mock_client.get_user.return_value = {"id": "user1", "name": "User 1"}
        
        with patch.object(handler, '_client', mock_client):
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            
            result = await handler.get_user("user1")
            
            assert result["name"] == "User 1"


class TestPMServiceHandlerProviders:
    """Tests for provider operations."""
    
    @pytest.mark.asyncio
    async def test_list_providers(self, handler, mock_client):
        """Test listing providers."""
        mock_client.list_providers.return_value = {
            "items": [{"id": "prov1", "name": "Provider 1"}],
            "total": 1
        }
        
        with patch.object(handler, '_client', mock_client):
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            
            result = await handler.list_providers()
            
            assert len(result) == 1
            assert result[0]["name"] == "Provider 1"
    
    @pytest.mark.asyncio
    async def test_sync_provider(self, handler, mock_client):
        """Test syncing a provider."""
        mock_client.sync_provider.return_value = {"success": True}
        
        with patch.object(handler, '_client', mock_client):
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            
            result = await handler.sync_provider(
                backend_provider_id="backend1",
                provider_type="openproject",
                name="Test Provider",
                base_url="http://test.example.com"
            )
            
            assert result["success"] is True


class TestGetPMServiceHandler:
    """Tests for get_pm_service_handler function."""
    
    def test_returns_handler_with_user_id(self):
        """Test returns handler with user ID."""
        handler = get_pm_service_handler(user_id="user123")
        assert handler.user_id == "user123"
    
    def test_returns_handler_without_user_id(self):
        """Test returns handler without user ID."""
        handler = get_pm_service_handler()
        assert handler.user_id is None


