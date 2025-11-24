# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
Unit tests for MCPPMHandler health check functionality
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from uuid import uuid4
from sqlalchemy.orm import Session

from mcp_server.pm_handler import MCPPMHandler
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


@pytest.mark.asyncio
async def test_health_check_providers_no_providers(mock_db_session):
    """Test health check with no providers"""
    handler = MCPPMHandler(db_session=mock_db_session)
    mock_db_session.query.return_value.filter.return_value.all.return_value = []
    
    result = await handler.health_check_providers()
    
    assert result["total"] == 0
    assert result["healthy"] == 0
    assert result["unhealthy"] == 0
    assert result["results"] == []
    assert result["actions_taken"] == []


@pytest.mark.asyncio
async def test_health_check_providers_no_db_session():
    """Test health check with no database session"""
    handler = MCPPMHandler(db_session=None)
    
    result = await handler.health_check_providers()
    
    assert result["total"] == 0
    assert result["healthy"] == 0
    assert result["unhealthy"] == 0
    assert result["results"] == []
    assert result["actions_taken"] == []


@pytest.mark.asyncio
@patch("mcp_server.pm_handler.create_pm_provider")
async def test_health_check_providers_healthy_provider(
    mock_create_provider, mock_db_session, mock_provider, mock_provider_instance
):
    """Test health check with a healthy provider"""
    handler = MCPPMHandler(db_session=mock_db_session)
    
    # Setup query chain
    query_mock = MagicMock()
    query_mock.filter.return_value = query_mock
    query_mock.all.return_value = [mock_provider]
    mock_db_session.query.return_value = query_mock
    
    # Setup provider instance
    mock_create_provider.return_value = mock_provider_instance
    mock_provider_instance.health_check.return_value = True
    
    result = await handler.health_check_providers()
    
    assert result["total"] == 1
    assert result["healthy"] == 1
    assert result["unhealthy"] == 0
    assert len(result["results"]) == 1
    assert result["results"][0]["healthy"] is True
    assert result["results"][0]["provider_id"] == str(mock_provider.id)
    assert result["actions_taken"] == []


@pytest.mark.asyncio
@patch("mcp_server.pm_handler.create_pm_provider")
async def test_health_check_providers_unhealthy_provider(
    mock_create_provider, mock_db_session, mock_provider, mock_provider_instance
):
    """Test health check with an unhealthy provider"""
    handler = MCPPMHandler(db_session=mock_db_session)
    
    # Setup query chain
    query_mock = MagicMock()
    query_mock.filter.return_value = query_mock
    query_mock.all.return_value = [mock_provider]
    mock_db_session.query.return_value = query_mock
    
    # Setup provider instance - health check fails
    mock_create_provider.return_value = mock_provider_instance
    mock_provider_instance.health_check.return_value = False
    
    result = await handler.health_check_providers()
    
    assert result["total"] == 1
    assert result["healthy"] == 0
    assert result["unhealthy"] == 1
    assert len(result["results"]) == 1
    assert result["results"][0]["healthy"] is False
    assert result["results"][0]["error"] == "Health check failed"
    assert result["actions_taken"] == []  # No auto_fix, so no actions


@pytest.mark.asyncio
@patch("mcp_server.pm_handler.create_pm_provider")
async def test_health_check_providers_auto_fix_deactivate(
    mock_create_provider, mock_db_session, mock_provider, mock_provider_instance
):
    """Test health check with auto_fix=True (deactivate unhealthy provider)"""
    handler = MCPPMHandler(db_session=mock_db_session)
    
    # Setup query chain
    query_mock = MagicMock()
    query_mock.filter.return_value = query_mock
    query_mock.all.return_value = [mock_provider]
    mock_db_session.query.return_value = query_mock
    
    # Setup provider instance - health check fails
    mock_create_provider.return_value = mock_provider_instance
    mock_provider_instance.health_check.return_value = False
    
    result = await handler.health_check_providers(auto_fix=True, delete_unreachable=False)
    
    assert result["total"] == 1
    assert result["healthy"] == 0
    assert result["unhealthy"] == 1
    assert len(result["actions_taken"]) == 1
    assert result["actions_taken"][0]["action"] == "deactivated"
    assert result["actions_taken"][0]["provider_id"] == str(mock_provider.id)
    # Verify provider was marked as inactive
    assert mock_provider.is_active is False
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
@patch("mcp_server.pm_handler.create_pm_provider")
async def test_health_check_providers_auto_fix_delete(
    mock_create_provider, mock_db_session, mock_provider, mock_provider_instance
):
    """Test health check with auto_fix=True and delete_unreachable=True"""
    handler = MCPPMHandler(db_session=mock_db_session)
    
    # Setup query chain
    query_mock = MagicMock()
    query_mock.filter.return_value = query_mock
    query_mock.all.return_value = [mock_provider]
    mock_db_session.query.return_value = query_mock
    
    # Setup provider instance - health check fails
    mock_create_provider.return_value = mock_provider_instance
    mock_provider_instance.health_check.return_value = False
    
    result = await handler.health_check_providers(auto_fix=True, delete_unreachable=True)
    
    assert result["total"] == 1
    assert result["healthy"] == 0
    assert result["unhealthy"] == 1
    assert len(result["actions_taken"]) == 1
    assert result["actions_taken"][0]["action"] == "deleted"
    assert result["actions_taken"][0]["provider_id"] == str(mock_provider.id)
    # Verify provider was deleted
    mock_db_session.delete.assert_called_once_with(mock_provider)
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
@patch("mcp_server.pm_handler.create_pm_provider")
async def test_health_check_providers_exception_during_check(
    mock_create_provider, mock_db_session, mock_provider
):
    """Test health check when provider creation or health check raises an exception"""
    handler = MCPPMHandler(db_session=mock_db_session)
    
    # Setup query chain
    query_mock = MagicMock()
    query_mock.filter.return_value = query_mock
    query_mock.all.return_value = [mock_provider]
    mock_db_session.query.return_value = query_mock
    
    # Setup provider creation to raise an exception
    mock_create_provider.side_effect = ConnectionError("Connection failed")
    
    result = await handler.health_check_providers()
    
    assert result["total"] == 1
    assert result["healthy"] == 0
    assert result["unhealthy"] == 1
    assert len(result["results"]) == 1
    assert result["results"][0]["healthy"] is False
    assert "Connection failed" in result["results"][0]["error"]
    assert result["actions_taken"] == []  # No auto_fix, so no actions


@pytest.mark.asyncio
@patch("mcp_server.pm_handler.create_pm_provider")
async def test_health_check_providers_exception_with_auto_fix(
    mock_create_provider, mock_db_session, mock_provider
):
    """Test health check with exception and auto_fix enabled"""
    handler = MCPPMHandler(db_session=mock_db_session)
    
    # Setup query chain
    query_mock = MagicMock()
    query_mock.filter.return_value = query_mock
    query_mock.all.return_value = [mock_provider]
    mock_db_session.query.return_value = query_mock
    
    # Setup provider creation to raise an exception
    mock_create_provider.side_effect = ConnectionError("Connection failed")
    
    result = await handler.health_check_providers(auto_fix=True, delete_unreachable=False)
    
    assert result["total"] == 1
    assert result["healthy"] == 0
    assert result["unhealthy"] == 1
    assert len(result["actions_taken"]) == 1
    assert result["actions_taken"][0]["action"] == "deactivated"
    assert "Connection failed" in result["actions_taken"][0]["reason"]
    # Verify provider was marked as inactive
    assert mock_provider.is_active is False
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
@patch("mcp_server.pm_handler.create_pm_provider")
async def test_health_check_providers_multiple_providers(
    mock_create_provider, mock_db_session, mock_provider_instance
):
    """Test health check with multiple providers (some healthy, some unhealthy)"""
    handler = MCPPMHandler(db_session=mock_db_session)
    
    # Create multiple mock providers
    provider1 = MagicMock(spec=PMProviderConnection)
    provider1.id = uuid4()
    provider1.name = "Provider 1"
    provider1.provider_type = "jira"
    provider1.base_url = "https://test1.atlassian.net"
    provider1.is_active = True
    provider1.api_key = None
    provider1.api_token = "token1"
    provider1.username = "user1@example.com"
    provider1.organization_id = None
    provider1.workspace_id = None
    
    provider2 = MagicMock(spec=PMProviderConnection)
    provider2.id = uuid4()
    provider2.name = "Provider 2"
    provider2.provider_type = "openproject"
    provider2.base_url = "https://test2.openproject.com"
    provider2.is_active = True
    provider2.api_key = "key2"
    provider2.api_token = None
    provider2.username = None
    provider2.organization_id = None
    provider2.workspace_id = None
    
    # Setup query chain
    query_mock = MagicMock()
    query_mock.filter.return_value = query_mock
    query_mock.all.return_value = [provider1, provider2]
    mock_db_session.query.return_value = query_mock
    
    # Setup provider instances - first healthy, second unhealthy
    instance1 = MagicMock()
    instance1.health_check = AsyncMock(return_value=True)
    instance2 = MagicMock()
    instance2.health_check = AsyncMock(return_value=False)
    
    mock_create_provider.side_effect = [instance1, instance2]
    
    result = await handler.health_check_providers()
    
    assert result["total"] == 2
    assert result["healthy"] == 1
    assert result["unhealthy"] == 1
    assert len(result["results"]) == 2
    assert result["results"][0]["healthy"] is True
    assert result["results"][1]["healthy"] is False


@pytest.mark.asyncio
@patch("mcp_server.pm_handler.create_pm_provider")
async def test_health_check_providers_user_filtered(
    mock_create_provider, mock_db_session, mock_provider, mock_provider_instance
):
    """Test health check with user_id filter"""
    user_id = uuid4()
    handler = MCPPMHandler(db_session=mock_db_session, user_id=str(user_id))
    
    # Setup query chain
    query_mock = MagicMock()
    query_mock.filter.return_value = query_mock
    query_mock.all.return_value = [mock_provider]
    mock_db_session.query.return_value = query_mock
    
    # Setup provider instance
    mock_create_provider.return_value = mock_provider_instance
    mock_provider_instance.health_check.return_value = True
    
    result = await handler.health_check_providers()
    
    # Verify user filter was applied
    mock_db_session.query.assert_called_with(PMProviderConnection)
    # The filter chain should include user_id filter
    assert result["total"] == 1


