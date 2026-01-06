
import pytest
import asyncio
from unittest.mock import MagicMock
from typing import AsyncIterator
from pm_service.handlers.pm_handler import PMHandler

# Mock Provider
class MockProvider:
    def __init__(self, count=1000, delay=0):
        self.count = count
        self.delay = delay
        self.id = "mock_provider"
        self.name = "Mock Provider"

    async def list_tasks(self, **kwargs) -> AsyncIterator[dict]:
        for i in range(self.count):
            yield {
                "id": str(i),
                "title": f"Task {i}",
                "status": "open",
                "provider_id": self.id
            }
            if self.delay and i % 100 == 0:
                await asyncio.sleep(self.delay)

    async def get_time_entries(self, **kwargs) -> AsyncIterator[dict]:
        for i in range(self.count):
            yield {
                "id": str(i),
                "hours": 1.0,
                "user_id": "user1",
                "provider_id": self.id
            }

# Mock Connection
class MockConnection:
    def __init__(self):
        self.id = "mock_conn_id"
        self.name = "Mock Connection"
        self.backend_provider_id = None
        self.provider_type = "mock"

    def get_provider_config(self):
        return {}

@pytest.mark.asyncio
async def test_list_tasks_streaming():
    # Setup
    db_mock = MagicMock()
    handler = PMHandler(db_session=db_mock)
    
    # Patch internals
    handler.get_active_providers = lambda: [MockConnection()]
    handler.create_provider_instance = lambda conn: MockProvider(count=500)
    handler.get_provider_by_id = lambda pid: MockConnection()
    
    # Run
    tasks = await handler.list_tasks()
    
    # Verify
    assert len(tasks) == 500
    assert tasks[0]["id"] == "0"
    assert tasks[-1]["id"] == "499"

@pytest.mark.asyncio
async def test_list_time_entries_streaming():
    # Setup
    db_mock = MagicMock()
    handler = PMHandler(db_session=db_mock)
    
    # Patch internals
    handler.get_active_providers = lambda: [MockConnection()]
    handler.create_provider_instance = lambda conn: MockProvider(count=500)
    
    # Run
    entries = await handler.list_time_entries()
    
    # Verify
    assert len(entries) == 500
    assert entries[0]["hours"] == 1.0
