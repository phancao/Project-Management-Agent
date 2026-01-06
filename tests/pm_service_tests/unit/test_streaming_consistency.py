
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from pm_service.handlers.pm_handler import PMHandler
from pm_service.providers.base import BasePMProvider
from pm_service.utils.data_buffer import DataBuffer

class MockStreamingProvider(BasePMProvider):
    def __init__(self, config=None):
        self.config = config
        self.id = "mock_provider"
        self.name = "Mock Provider"

    async def list_projects(self, user_id=None):
        # Yields items (AsyncIterator)
        for i in range(5):
            yield {"id": str(i), "name": f"Project {i}"}

    async def list_users(self, project_id=None):
        # Returns List (testing compatibility)
        return [{"id": "u1", "name": "User 1"}, {"id": "u2", "name": "User 2"}]

    async def list_sprints(self, project_id=None, state=None):
        for i in range(3):
            yield {"id": f"s{i}", "name": f"Sprint {i}", "status": "open"}

    async def list_epics(self, project_id=None):
        for i in range(2):
            yield {"id": f"e{i}", "name": f"Epic {i}"}
    
    # Required abstract methods (dummies)
    async def get_project(self, project_id): pass
    async def create_project(self, project): pass
    async def update_project(self, project_id, updates): pass
    async def delete_project(self, project_id): pass
    async def list_tasks(self, **kwargs): pass
    async def get_task(self, task_id): pass
    async def create_task(self, task): pass
    async def update_task(self, task_id, updates): pass
    async def delete_task(self, task_id): pass
    async def get_sprint(self, sprint_id): pass
    async def create_sprint(self, sprint): pass
    async def update_sprint(self, sprint_id, updates): pass
    async def delete_sprint(self, sprint_id): pass
    async def get_user(self, user_id): pass
    async def get_epic(self, epic_id): pass
    async def create_epic(self, epic): pass
    async def update_epic(self, epic_id, updates): pass
    async def delete_epic(self, epic_id): pass
    async def list_labels(self, project_id=None): pass
    async def get_label(self, label_id): pass
    async def create_label(self, label): pass
    async def update_label(self, label_id, updates): pass
    async def delete_label(self, label_id): pass
    async def list_statuses(self, entity_type, project_id=None): pass
    async def get_time_entries(self, **kwargs): pass
    async def health_check(self): return True

@pytest.fixture
def mock_handler():
    mock_db = MagicMock()
    handler = PMHandler(db_session=mock_db)
    handler.get_active_providers = MagicMock(return_value=[MagicMock(id="mock", name="Mock", backend_provider_id=None)])
    # Mock create_provider_instance to return our MockStreamingProvider
    handler.create_provider_instance = MagicMock(return_value=MockStreamingProvider())
    
    # Mock provider connection object
    conn = MagicMock()
    conn.id = "mock"
    conn.name = "Mock Provider"
    conn.backend_provider_id = None
    handler.get_active_providers.return_value = [conn]
    
    # Mock to_dict to just return dict (bypass pydantic)
    handler._to_dict = lambda x: x if isinstance(x, dict) else x.dict()
    return handler

@pytest.mark.asyncio
async def test_list_projects_streaming(mock_handler):
    projects = await mock_handler.list_projects()
    assert len(projects) == 5
    assert projects[0]["id"] == "mock:0"
    assert projects[4]["id"] == "mock:4"

@pytest.mark.asyncio
async def test_list_users_compatibility(mock_handler):
    # This tests ensure_async_iterator with a List return
    users = await mock_handler.list_users()
    assert len(users) == 2
    assert users[0]["id"] == "mock:u1"

@pytest.mark.asyncio
async def test_list_sprints_streaming(mock_handler):
    sprints = await mock_handler.list_sprints()
    assert len(sprints) == 3
    assert sprints[0]["id"] == "mock:s0"

@pytest.mark.asyncio
async def test_list_epics_streaming(mock_handler):
    epics = await mock_handler.list_epics()
    assert len(epics) == 2
    assert epics[0]["id"] == "mock:e0"
