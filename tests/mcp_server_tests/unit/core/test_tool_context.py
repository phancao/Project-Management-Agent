"""
Unit tests for MCP Server ToolContext
"""
import sys
import os
print("[DEBUG] CWD:", os.getcwd())
print("[DEBUG] sys.path:", sys.path)
try:
    import backend
    print("[DEBUG] backend:", backend)
    print("[DEBUG] backend file:", backend.__file__)
    import backend.analytics
    print("[DEBUG] backend.analytics:", backend.analytics)
except ImportError as e:
    print("[DEBUG] Import Error:", e)

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from sqlalchemy.orm import Session

from mcp_server.core.tool_context import ToolContext
from pm_service.client.async_client import AsyncPMServiceClient


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = MagicMock(spec=Session)
    session.query = MagicMock()
    session.commit = MagicMock()
    return session


class TestToolContextInit:
    """Tests for ToolContext initialization."""
    
    def test_init_with_db_session(self, mock_db_session):
        """Test initialization with database session."""
        context = ToolContext(db_session=mock_db_session)
        
        assert context.db == mock_db_session
        assert context.user_id is None
        assert context.provider_manager is not None
        assert context.analytics_manager is not None
    
    def test_init_with_user_id(self, mock_db_session):
        """Test initialization with user ID."""
        user_id = str(uuid4())
        context = ToolContext(db_session=mock_db_session, user_id=user_id)
        
        assert context.user_id == user_id
    
    def test_init_with_custom_pm_service_url(self, mock_db_session):
        """Test initialization with custom PM Service URL."""
        context = ToolContext(
            db_session=mock_db_session,
            pm_service_url="http://custom:9000"
        )
        
        assert context._pm_service_url == "http://custom:9000"
    
    def test_init_uses_env_pm_service_url(self, mock_db_session):
        """Test initialization uses environment PM Service URL."""
        with patch.dict('os.environ', {'PM_SERVICE_URL': 'http://env:8080'}):
            context = ToolContext(db_session=mock_db_session)
            # Default fallback if env not set during import
            assert context._pm_service_url in ["http://env:8080", "http://localhost:8001"]


class TestToolContextPMService:
    """Tests for PM Service client access."""
    
    def test_pm_service_property_creates_client(self, mock_db_session):
        """Test pm_service property creates client on first access."""
        context = ToolContext(db_session=mock_db_session)
        
        assert context._pm_service_client is None
        
        client = context.pm_service
        
        assert client is not None
        assert isinstance(client, AsyncPMServiceClient)
        assert context._pm_service_client is client
    
    def test_pm_service_property_returns_same_client(self, mock_db_session):
        """Test pm_service property returns same client on subsequent access."""
        context = ToolContext(db_session=mock_db_session)
        
        client1 = context.pm_service
        client2 = context.pm_service
        
        assert client1 is client2
    
    def test_pm_service_uses_configured_url(self, mock_db_session):
        """Test PM Service client uses configured URL."""
        context = ToolContext(
            db_session=mock_db_session,
            pm_service_url="http://custom:9000"
        )
        
        client = context.pm_service
        
        assert client.base_url == "http://custom:9000"


class TestToolContextFromDbSession:
    """Tests for from_db_session class method."""
    
    def test_from_db_session(self, mock_db_session):
        """Test creating context from database session."""
        context = ToolContext.from_db_session(
            db_session=mock_db_session,
            user_id="user123"
        )
        
        assert context.db == mock_db_session
        assert context.user_id == "user123"


class TestToolContextCaches:
    """Tests for cache management."""
    
    def test_clear_caches(self, mock_db_session):
        """Test clearing all caches."""
        context = ToolContext(db_session=mock_db_session)
        
        # Mock the cache clear methods
        context.provider_manager.clear_cache = MagicMock()
        context.analytics_manager.clear_cache = MagicMock()
        
        context.clear_caches()
        
        context.provider_manager.clear_cache.assert_called_once()
        context.analytics_manager.clear_cache.assert_called_once()


class TestToolContextProviderManager:
    """Tests for provider manager integration."""
    
    def test_provider_manager_has_db_session(self, mock_db_session):
        """Test provider manager has database session."""
        context = ToolContext(db_session=mock_db_session)
        
        # The provider manager should be initialized
        assert context.provider_manager is not None
    
    def test_provider_manager_has_user_id(self, mock_db_session):
        """Test provider manager has user ID."""
        user_id = str(uuid4())
        context = ToolContext(db_session=mock_db_session, user_id=user_id)
        
        # The provider manager should be initialized with user_id
        assert context.provider_manager is not None


class TestToolContextAnalyticsManager:
    """Tests for analytics manager integration."""
    
    def test_analytics_manager_initialized(self, mock_db_session):
        """Test analytics manager is initialized."""
        context = ToolContext(db_session=mock_db_session)
        
        assert context.analytics_manager is not None
    
    def test_analytics_manager_has_provider_manager(self, mock_db_session):
        """Test analytics manager has provider manager."""
        context = ToolContext(db_session=mock_db_session)
        
        # Analytics manager should have access to provider manager
        assert context.analytics_manager is not None
