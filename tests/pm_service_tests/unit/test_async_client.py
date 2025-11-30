"""
Unit tests for PM Service AsyncPMServiceClient
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from pm_service.client.async_client import AsyncPMServiceClient, get_pm_service_client


@pytest.fixture
def mock_response():
    """Create a mock HTTP response."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"items": [], "total": 0}
    response.raise_for_status = MagicMock()
    return response


@pytest.fixture
def client():
    """Create an AsyncPMServiceClient instance."""
    return AsyncPMServiceClient(
        base_url="http://localhost:8001",
        timeout=5.0,
        max_retries=1,
        retry_delay=0.1
    )


class TestAsyncPMServiceClientInit:
    """Tests for client initialization."""
    
    def test_default_init(self):
        """Test default initialization."""
        client = AsyncPMServiceClient()
        assert client.base_url == "http://localhost:8001"
        assert client.timeout == 30.0
        assert client.max_retries == 3
    
    def test_custom_init(self):
        """Test custom initialization."""
        client = AsyncPMServiceClient(
            base_url="http://custom:9000",
            timeout=10.0,
            max_retries=5,
            retry_delay=2.0
        )
        assert client.base_url == "http://custom:9000"
        assert client.timeout == 10.0
        assert client.max_retries == 5
        assert client.retry_delay == 2.0
    
    def test_trailing_slash_removed(self):
        """Test trailing slash is removed from base URL."""
        client = AsyncPMServiceClient(base_url="http://localhost:8001/")
        assert client.base_url == "http://localhost:8001"


class TestAsyncPMServiceClientContextManager:
    """Tests for async context manager."""
    
    @pytest.mark.asyncio
    async def test_enter_creates_client(self, client):
        """Test entering context creates HTTP client."""
        assert client._client is None
        
        async with client:
            assert client._client is not None
            assert isinstance(client._client, httpx.AsyncClient)
    
    @pytest.mark.asyncio
    async def test_exit_closes_client(self, client):
        """Test exiting context closes HTTP client."""
        async with client:
            pass
        
        assert client._client is None


class TestAsyncPMServiceClientProjects:
    """Tests for project operations."""
    
    @pytest.mark.asyncio
    async def test_list_projects(self, client, mock_response):
        """Test listing projects."""
        mock_response.json.return_value = {
            "items": [{"id": "proj1", "name": "Project 1"}],
            "total": 1
        }
        
        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response.json.return_value
            
            result = await client.list_projects()
            
            mock_request.assert_called_once_with(
                "GET", "/api/v1/projects",
                params={"limit": 100, "offset": 0}
            )
            assert result["total"] == 1
            assert len(result["items"]) == 1
    
    @pytest.mark.asyncio
    async def test_list_projects_with_filters(self, client):
        """Test listing projects with filters."""
        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"items": [], "total": 0}
            
            await client.list_projects(
                provider_id="prov1",
                user_id="user1",
                limit=50,
                offset=10
            )
            
            mock_request.assert_called_once_with(
                "GET", "/api/v1/projects",
                params={
                    "limit": 50,
                    "offset": 10,
                    "provider_id": "prov1",
                    "user_id": "user1"
                }
            )
    
    @pytest.mark.asyncio
    async def test_get_project(self, client):
        """Test getting a project."""
        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"id": "proj1", "name": "Project 1"}
            
            result = await client.get_project("prov1:proj1")
            
            mock_request.assert_called_once_with(
                "GET", "/api/v1/projects/prov1:proj1"
            )
            assert result["name"] == "Project 1"


class TestAsyncPMServiceClientTasks:
    """Tests for task operations."""
    
    @pytest.mark.asyncio
    async def test_list_tasks(self, client):
        """Test listing tasks."""
        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"items": [], "total": 0}
            
            await client.list_tasks()
            
            mock_request.assert_called_once_with(
                "GET", "/api/v1/tasks",
                params={"limit": 100, "offset": 0}
            )
    
    @pytest.mark.asyncio
    async def test_list_tasks_with_filters(self, client):
        """Test listing tasks with filters."""
        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"items": [], "total": 0}
            
            await client.list_tasks(
                project_id="proj1",
                sprint_id="sprint1",
                assignee_id="user1",
                status="open"
            )
            
            mock_request.assert_called_once()
            call_params = mock_request.call_args[1]["params"]
            assert call_params["project_id"] == "proj1"
            assert call_params["sprint_id"] == "sprint1"
            assert call_params["assignee_id"] == "user1"
            assert call_params["status"] == "open"
    
    @pytest.mark.asyncio
    async def test_get_task(self, client):
        """Test getting a task."""
        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"id": "task1", "title": "Task 1"}
            
            result = await client.get_task("prov1:task1")
            
            mock_request.assert_called_once_with(
                "GET", "/api/v1/tasks/prov1:task1"
            )
            assert result["title"] == "Task 1"
    
    @pytest.mark.asyncio
    async def test_create_task(self, client):
        """Test creating a task."""
        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"id": "task1", "title": "New Task"}
            
            result = await client.create_task(
                project_id="proj1",
                title="New Task",
                description="Description",
                story_points=5
            )
            
            mock_request.assert_called_once()
            call_json = mock_request.call_args[1]["json"]
            assert call_json["project_id"] == "proj1"
            assert call_json["title"] == "New Task"
            assert call_json["description"] == "Description"
            assert call_json["story_points"] == 5
    
    @pytest.mark.asyncio
    async def test_update_task(self, client):
        """Test updating a task."""
        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"id": "task1", "title": "Updated Task"}
            
            result = await client.update_task(
                task_id="prov1:task1",
                title="Updated Task",
                status="done"
            )
            
            mock_request.assert_called_once()
            call_json = mock_request.call_args[1]["json"]
            assert call_json["title"] == "Updated Task"
            assert call_json["status"] == "done"


class TestAsyncPMServiceClientSprints:
    """Tests for sprint operations."""
    
    @pytest.mark.asyncio
    async def test_list_sprints(self, client):
        """Test listing sprints."""
        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"items": [], "total": 0}
            
            await client.list_sprints(project_id="proj1")
            
            mock_request.assert_called_once()
            call_params = mock_request.call_args[1]["params"]
            assert call_params["project_id"] == "proj1"
    
    @pytest.mark.asyncio
    async def test_get_sprint(self, client):
        """Test getting a sprint."""
        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"id": "sprint1", "name": "Sprint 1"}
            
            result = await client.get_sprint("prov1:sprint1")
            
            mock_request.assert_called_once_with(
                "GET", "/api/v1/sprints/prov1:sprint1"
            )
            assert result["name"] == "Sprint 1"
    
    @pytest.mark.asyncio
    async def test_get_sprint_tasks(self, client):
        """Test getting sprint tasks."""
        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"items": [], "total": 0}
            
            await client.get_sprint_tasks("prov1:sprint1")
            
            mock_request.assert_called_once()
            assert "/api/v1/sprints/prov1:sprint1/tasks" in str(mock_request.call_args)


class TestAsyncPMServiceClientUsers:
    """Tests for user operations."""
    
    @pytest.mark.asyncio
    async def test_list_users(self, client):
        """Test listing users."""
        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"items": [], "total": 0}
            
            await client.list_users(project_id="proj1")
            
            mock_request.assert_called_once()
            call_params = mock_request.call_args[1]["params"]
            assert call_params["project_id"] == "proj1"
    
    @pytest.mark.asyncio
    async def test_get_user(self, client):
        """Test getting a user."""
        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"id": "user1", "name": "User 1"}
            
            result = await client.get_user("prov1:user1")
            
            mock_request.assert_called_once_with(
                "GET", "/api/v1/users/prov1:user1"
            )
            assert result["name"] == "User 1"


class TestAsyncPMServiceClientProviders:
    """Tests for provider operations."""
    
    @pytest.mark.asyncio
    async def test_list_providers(self, client):
        """Test listing providers."""
        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"items": [], "total": 0}
            
            await client.list_providers()
            
            mock_request.assert_called_once_with("GET", "/api/v1/providers")
    
    @pytest.mark.asyncio
    async def test_sync_provider(self, client):
        """Test syncing a provider."""
        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"success": True}
            
            await client.sync_provider(
                backend_provider_id="backend1",
                provider_type="openproject",
                name="Test Provider",
                base_url="http://test.example.com",
                api_key="key123"
            )
            
            mock_request.assert_called_once()
            call_json = mock_request.call_args[1]["json"]
            assert call_json["backend_provider_id"] == "backend1"
            assert call_json["provider_type"] == "openproject"
            assert call_json["api_key"] == "key123"
    
    @pytest.mark.asyncio
    async def test_delete_provider(self, client):
        """Test deleting a provider."""
        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"success": True}
            
            await client.delete_provider("prov1")
            
            mock_request.assert_called_once_with(
                "DELETE", "/api/v1/providers/prov1"
            )


class TestAsyncPMServiceClientHealth:
    """Tests for health check."""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check."""
        with patch.object(client, '_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"status": "healthy"}
            
            result = await client.health_check()
            
            mock_request.assert_called_once_with("GET", "/health")
            assert result["status"] == "healthy"


class TestGetPMServiceClient:
    """Tests for get_pm_service_client function."""
    
    def test_returns_new_client_with_custom_url(self):
        """Test returns new client with custom URL."""
        client = get_pm_service_client("http://custom:9000")
        assert client.base_url == "http://custom:9000"
    
    def test_returns_default_client_without_url(self):
        """Test returns default client without URL."""
        client1 = get_pm_service_client()
        client2 = get_pm_service_client()
        assert client1 is client2


