# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
Unit tests for ToolContext and ProviderManager health check functionality

Note: These tests were migrated from MCPPMHandler tests after the PM Handler
was removed and replaced with ToolContext + ProviderManager.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from sqlalchemy.orm import Session

from mcp_server.core.tool_context import ToolContext
from mcp_server.core.provider_manager import ProviderManager
from mcp_server.database.models import PMProviderConnection


@pytest.fixture
def mock_db_session():
    """Create a mock database session"""
    session = MagicMock(spec=Session)
    session.query = MagicMock()
    session.commit = MagicMock()
    session.delete = MagicMock()
    return session


@pytest.fixture
def mock_provider():
    """Create a mock provider connection"""
    provider = MagicMock(spec=PMProviderConnection)
    provider.id = uuid4()
    provider.name = "Test Provider"
    provider.provider_type = "jira"
    provider.base_url = "https://test.atlassian.net"
    provider.is_active = True
    provider.api_key = None
    provider.api_token = "test_token"
    provider.username = "test@example.com"
    provider.organization_id = None
    provider.workspace_id = None
    return provider


@pytest.fixture
def mock_provider_instance():
    """Create a mock provider instance"""
    instance = MagicMock()
    instance.health_check = AsyncMock(return_value=True)
    return instance


@pytest.fixture
def tool_context(mock_db_session):
    """Create a ToolContext with mocked dependencies."""
    context = ToolContext(db_session=mock_db_session)
    return context


class TestToolContextInitialization:
    """Tests for ToolContext initialization."""
    
    def test_tool_context_creates_provider_manager(self, mock_db_session):
        """Test that ToolContext creates a ProviderManager."""
        context = ToolContext(db_session=mock_db_session)
        
        assert context.provider_manager is not None
        assert context.db == mock_db_session
    
    def test_tool_context_with_user_id(self, mock_db_session):
        """Test ToolContext with user_id."""
        user_id = str(uuid4())
        context = ToolContext(db_session=mock_db_session, user_id=user_id)
        
        assert context.user_id == user_id


class TestProviderManagerHealthCheck:
    """Tests for ProviderManager health check functionality."""
    
    def test_get_active_providers_no_providers(self, mock_db_session):
        """Test getting active providers when none exist."""
        mock_db_session.query.return_value.filter.return_value.all.return_value = []
        
        context = ToolContext(db_session=mock_db_session)
        providers = context.provider_manager.get_active_providers()
        
        assert providers == []
    
    def test_get_active_providers_with_providers(self, mock_db_session, mock_provider):
        """Test getting active providers when some exist."""
        # Setup query chain
        query_mock = MagicMock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = [mock_provider]
        mock_db_session.query.return_value = query_mock
        
        context = ToolContext(db_session=mock_db_session)
        providers = context.provider_manager.get_active_providers()
        
        assert len(providers) == 1
        assert providers[0].id == mock_provider.id


class TestToolContextCacheManagement:
    """Tests for ToolContext cache management."""
    
    def test_clear_caches(self, mock_db_session):
        """Test clearing caches."""
        context = ToolContext(db_session=mock_db_session)
        
        # This should not raise any errors
        context.clear_caches()


class TestProviderManagerProviderCreation:
    """Tests for ProviderManager provider instance creation."""
    
    @patch("mcp_server.core.provider_manager.create_pm_provider")
    def test_create_provider_instance(self, mock_create_provider, mock_db_session, mock_provider, mock_provider_instance):
        """Test creating a provider instance."""
        mock_create_provider.return_value = mock_provider_instance
        
        context = ToolContext(db_session=mock_db_session)
        instance = context.provider_manager.create_provider_instance(mock_provider)
        
        assert instance == mock_provider_instance
        mock_create_provider.assert_called_once()
    
    @patch("mcp_server.core.provider_manager.create_pm_provider")
    def test_create_provider_instance_error(self, mock_create_provider, mock_db_session, mock_provider):
        """Test error handling when creating provider instance fails."""
        mock_create_provider.side_effect = ConnectionError("Connection failed")
        
        context = ToolContext(db_session=mock_db_session)
        
        with pytest.raises(ConnectionError):
            context.provider_manager.create_provider_instance(mock_provider)


class TestProviderManagerGetProvider:
    """Tests for ProviderManager.get_provider async method."""
    
    @pytest.mark.asyncio
    @patch("mcp_server.core.provider_manager.create_pm_provider")
    async def test_get_provider_by_id(self, mock_create_provider, mock_db_session, mock_provider, mock_provider_instance):
        """Test getting a provider by ID."""
        # Setup query chain
        query_mock = MagicMock()
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = mock_provider
        mock_db_session.query.return_value = query_mock
        
        mock_create_provider.return_value = mock_provider_instance
        
        context = ToolContext(db_session=mock_db_session)
        provider = await context.provider_manager.get_provider(str(mock_provider.id))
        
        assert provider == mock_provider_instance
    
    @pytest.mark.asyncio
    async def test_get_provider_not_found(self, mock_db_session):
        """Test getting a provider that doesn't exist."""
        # Setup query chain to return None
        query_mock = MagicMock()
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = None
        mock_db_session.query.return_value = query_mock
        
        context = ToolContext(db_session=mock_db_session)
        
        with pytest.raises(ValueError, match="Provider .* not found"):
            await context.provider_manager.get_provider(str(uuid4()))


class TestProviderManagerErrorTracking:
    """Tests for ProviderManager error tracking."""
    
    def test_record_error(self, mock_db_session):
        """Test recording an error for a provider."""
        context = ToolContext(db_session=mock_db_session)
        provider_id = str(uuid4())
        error = Exception("Test error")
        
        # This should not raise any errors
        context.provider_manager.record_error(provider_id, error)

