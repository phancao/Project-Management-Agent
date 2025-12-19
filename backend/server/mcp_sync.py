"""
MCP Provider Sync Utility

This module provides functions to synchronize PM provider configurations
from the Backend to the MCP Server via HTTP API calls.

Since Backend and MCP Server are deployed on different cloud servers,
synchronization happens via HTTP API calls, not direct database access.

Authentication:
All sync requests include the PM_MCP_API_KEY header for authentication.
This ensures only the Backend can sync providers to the MCP Server.
"""

import logging
import os
from typing import Optional, Dict, Any
import httpx

logger = logging.getLogger(__name__)

# MCP Server URL - can be configured via environment variable
MCP_SERVER_URL = os.getenv("PM_MCP_SERVER_URL", "http://pm_mcp_server:8080")

# MCP API Key for authentication
MCP_API_KEY = os.getenv("PM_MCP_API_KEY", "")

# Timeout for sync operations (seconds)
SYNC_TIMEOUT = 30.0


def _get_auth_headers() -> Dict[str, str]:
    """Get authentication headers for MCP Server requests."""
    headers = {"Content-Type": "application/json"}
    if MCP_API_KEY:
        headers["X-MCP-API-Key"] = MCP_API_KEY
    else:
        logger.warning("[MCPSync] PM_MCP_API_KEY not set! Requests may fail authentication.")
    return headers


class MCPSyncError(Exception):
    """Exception raised when MCP sync fails."""
    pass


async def sync_provider_to_mcp(
    backend_provider_id: str,
    name: str,
    provider_type: str,
    base_url: str,
    api_key: Optional[str] = None,
    api_token: Optional[str] = None,
    username: Optional[str] = None,
    organization_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    project_key: Optional[str] = None,
    is_active: bool = True,
    test_connection: bool = True,
) -> Dict[str, Any]:
    """
    Sync a provider configuration from Backend to MCP Server.
    
    This function calls the MCP Server's /providers/sync endpoint to:
    1. Create or update the provider in MCP Server's database
    2. Optionally test the connection
    3. Return the MCP provider ID for Backend to store
    
    Args:
        backend_provider_id: Provider ID from Backend database
        name: Provider display name
        provider_type: Provider type (openproject_v13, jira, clickup, etc.)
        base_url: Provider base URL
        api_key: API key (for OpenProject, ClickUp)
        api_token: API token (for JIRA)
        username: Username (for JIRA)
        organization_id: Organization/Team ID
        workspace_id: Workspace ID
        project_key: Default project key
        is_active: Whether provider is active
        test_connection: Whether to test connection before saving
        
    Returns:
        Dict with sync result:
        - success: bool
        - action: str ("created", "updated")
        - mcp_provider_id: str (MCP Server's provider ID)
        - connection_tested: bool
        - connection_healthy: bool
        - message: str
        
    Raises:
        MCPSyncError: If sync fails
    """
    # Build the sync request
    sync_request = {
        "backend_provider_id": backend_provider_id,
        "name": name,
        "provider_type": provider_type,
        "base_url": base_url,
        "api_key": api_key,
        "api_token": api_token,
        "username": username,
        "organization_id": organization_id,
        "workspace_id": workspace_id,
        "project_key": project_key,
        "is_active": is_active,
        "test_connection": test_connection,
    }
    
    # Remove None values
    sync_request = {k: v for k, v in sync_request.items() if v is not None}
    
    # Get MCP Server URL (remove /sse suffix if present)
    mcp_url = MCP_SERVER_URL.replace("/sse", "").rstrip("/")
    sync_endpoint = f"{mcp_url}/providers/sync"
    
    logger.info(f"[MCPSync] Syncing provider {backend_provider_id} to MCP Server at {sync_endpoint}")
    
    try:
        async with httpx.AsyncClient(timeout=SYNC_TIMEOUT) as client:
            response = await client.post(
                sync_endpoint,
                json=sync_request,
                headers=_get_auth_headers()
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(
                    f"[MCPSync] Provider synced successfully: "
                    f"action={result.get('action')}, "
                    f"mcp_provider_id={result.get('mcp_provider_id')}"
                )
                return result
            else:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get("detail", error_detail)
                except:
                    pass
                    
                logger.error(
                    f"[MCPSync] Sync failed: status={response.status_code}, "
                    f"detail={error_detail}"
                )
                raise MCPSyncError(f"MCP sync failed: {error_detail}")
                
    except httpx.TimeoutException:
        logger.error(f"[MCPSync] Sync timeout after {SYNC_TIMEOUT}s")
        raise MCPSyncError(f"MCP sync timeout after {SYNC_TIMEOUT}s")
    except httpx.ConnectError as e:
        logger.error(f"[MCPSync] Cannot connect to MCP Server: {e}")
        raise MCPSyncError(f"Cannot connect to MCP Server at {mcp_url}: {e}")
    except Exception as e:
        logger.error(f"[MCPSync] Unexpected error: {e}", exc_info=True)
        raise MCPSyncError(f"MCP sync error: {e}")


async def delete_provider_from_mcp(
    backend_provider_id: str,
    hard_delete: bool = False,
) -> Dict[str, Any]:
    """
    Delete or deactivate a provider in MCP Server.
    
    Args:
        backend_provider_id: Provider ID from Backend database
        hard_delete: If True, delete provider. If False, just deactivate.
        
    Returns:
        Dict with delete result
        
    Raises:
        MCPSyncError: If delete fails
    """
    # Get MCP Server URL
    mcp_url = MCP_SERVER_URL.replace("/sse", "").rstrip("/")
    delete_endpoint = f"{mcp_url}/providers/sync"
    
    logger.info(f"[MCPSync] Deleting provider {backend_provider_id} from MCP Server")
    
    try:
        async with httpx.AsyncClient(timeout=SYNC_TIMEOUT) as client:
            response = await client.request(
                "DELETE",
                delete_endpoint,
                json={
                    "backend_provider_id": backend_provider_id,
                    "hard_delete": hard_delete,
                },
                headers=_get_auth_headers()
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"[MCPSync] Provider deleted: action={result.get('action')}")
                return result
            else:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get("detail", error_detail)
                except:
                    pass
                    
                logger.error(f"[MCPSync] Delete failed: {error_detail}")
                raise MCPSyncError(f"MCP delete failed: {error_detail}")
                
    except httpx.TimeoutException:
        logger.error(f"[MCPSync] Delete timeout")
        raise MCPSyncError("MCP delete timeout")
    except httpx.ConnectError as e:
        logger.error(f"[MCPSync] Cannot connect to MCP Server: {e}")
        raise MCPSyncError(f"Cannot connect to MCP Server: {e}")
    except Exception as e:
        logger.error(f"[MCPSync] Delete error: {e}", exc_info=True)
        raise MCPSyncError(f"MCP delete error: {e}")


async def bulk_sync_providers_to_mcp(
    providers: list[Dict[str, Any]],
    delete_missing: bool = False,
) -> Dict[str, Any]:
    """
    Sync multiple providers to MCP Server at once.
    
    Useful for initial sync or periodic reconciliation.
    
    Args:
        providers: List of provider configurations (same format as sync_provider_to_mcp args)
        delete_missing: If True, deactivate MCP providers not in the list
        
    Returns:
        Dict with bulk sync results
    """
    # Get MCP Server URL
    mcp_url = MCP_SERVER_URL.replace("/sse", "").rstrip("/")
    bulk_endpoint = f"{mcp_url}/providers/sync/bulk"
    
    logger.info(f"[MCPSync] Bulk syncing {len(providers)} providers to MCP Server")
    
    try:
        async with httpx.AsyncClient(timeout=SYNC_TIMEOUT * 2) as client:
            response = await client.post(
                bulk_endpoint,
                json={
                    "providers": providers,
                    "delete_missing": delete_missing,
                },
                headers=_get_auth_headers()
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(
                    f"[MCPSync] Bulk sync completed: "
                    f"synced={result.get('synced')}, "
                    f"failed={result.get('failed')}"
                )
                return result
            else:
                error_detail = response.text
                logger.error(f"[MCPSync] Bulk sync failed: {error_detail}")
                raise MCPSyncError(f"MCP bulk sync failed: {error_detail}")
                
    except Exception as e:
        logger.error(f"[MCPSync] Bulk sync error: {e}", exc_info=True)
        raise MCPSyncError(f"MCP bulk sync error: {e}")


async def get_mcp_sync_status() -> Dict[str, Any]:
    """
    Get the current sync status from MCP Server.
    
    Returns:
        Dict with sync status including all providers and their mapping status
    """
    # Get MCP Server URL
    mcp_url = MCP_SERVER_URL.replace("/sse", "").rstrip("/")
    status_endpoint = f"{mcp_url}/providers/sync/status"
    
    try:
        async with httpx.AsyncClient(timeout=SYNC_TIMEOUT) as client:
            response = await client.get(
                status_endpoint,
                headers=_get_auth_headers()
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"[MCPSync] Failed to get sync status: {response.text}")
                return {"error": response.text}
                
    except Exception as e:
        logger.error(f"[MCPSync] Error getting sync status: {e}")
        return {"error": str(e)}


async def test_mcp_provider_connection(mcp_provider_id: str) -> Dict[str, Any]:
    """
    Test connection for a specific provider in MCP Server.
    
    Args:
        mcp_provider_id: MCP Server's provider ID
        
    Returns:
        Dict with connection test result
    """
    # Get MCP Server URL
    mcp_url = MCP_SERVER_URL.replace("/sse", "").rstrip("/")
    test_endpoint = f"{mcp_url}/providers/sync/test/{mcp_provider_id}"
    
    try:
        async with httpx.AsyncClient(timeout=SYNC_TIMEOUT) as client:
            response = await client.post(
                test_endpoint,
                headers=_get_auth_headers()
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"[MCPSync] Connection test failed: {response.text}")
                return {"connection_healthy": False, "error": response.text}
                
    except Exception as e:
        logger.error(f"[MCPSync] Connection test error: {e}")
        return {"connection_healthy": False, "error": str(e)}


# Helper function to extract mcp_provider_id from additional_config
def get_mcp_provider_id(provider) -> Optional[str]:
    """
    Get the MCP provider ID from a Backend provider's additional_config.
    
    Args:
        provider: PMProviderConnection ORM object
        
    Returns:
        MCP provider ID string, or None if not synced
    """
    if provider.additional_config:
        return provider.additional_config.get("mcp_provider_id")
    return None


def set_mcp_provider_id(provider, mcp_provider_id: str) -> None:
    """
    Set the MCP provider ID in a Backend provider's additional_config.
    
    Args:
        provider: PMProviderConnection ORM object
        mcp_provider_id: MCP Server's provider ID
    """
    if not provider.additional_config:
        provider.additional_config = {}
    provider.additional_config["mcp_provider_id"] = mcp_provider_id


async def check_and_sync_providers():
    """
    Check all providers and sync any that are out of sync with MCP Server.
    
    This function:
    1. Gets all active providers from Backend
    2. Checks each provider's connection health in MCP Server
    3. Re-syncs any providers that have connection issues
    
    Call this periodically (e.g., every 5 minutes) to detect:
    - Expired tokens
    - Changed credentials
    - MCP Server restarts that lost provider data
    
    Returns:
        Dict with sync check results
    """
    from database.connection import get_db_session
    from database.orm_models import PMProviderConnection
    
    results = {
        "checked": 0,
        "synced": 0,
        "healthy": 0,
        "unhealthy": 0,
        "errors": [],
    }
    
    try:
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            # Get all active providers
            providers = db.query(PMProviderConnection).filter(
                PMProviderConnection.is_active.is_(True)
            ).all()
            
            results["checked"] = len(providers)
            
            for provider in providers:
                mcp_id = get_mcp_provider_id(provider)
                
                if not mcp_id:
                    # Provider not synced yet, sync it
                    try:
                        sync_result = await sync_provider_to_mcp(
                            backend_provider_id=str(provider.id),
                            name=provider.name,
                            provider_type=provider.provider_type,
                            base_url=provider.base_url,
                            api_key=provider.api_key,
                            api_token=provider.api_token,
                            username=provider.username,
                            organization_id=provider.organization_id,
                            workspace_id=provider.workspace_id,
                            is_active=True,
                            test_connection=True,
                        )
                        if sync_result.get("success"):
                            set_mcp_provider_id(provider, sync_result["mcp_provider_id"])
                            results["synced"] += 1
                            if sync_result.get("connection_healthy"):
                                results["healthy"] += 1
                            else:
                                results["unhealthy"] += 1
                    except MCPSyncError as e:
                        results["errors"].append(f"Provider {provider.id}: {e}")
                else:
                    # Provider already synced, test connection
                    test_result = await test_mcp_provider_connection(mcp_id)
                    if test_result.get("connection_healthy"):
                        results["healthy"] += 1
                    else:
                        # Connection unhealthy, re-sync
                        try:
                            sync_result = await sync_provider_to_mcp(
                                backend_provider_id=str(provider.id),
                                name=provider.name,
                                provider_type=provider.provider_type,
                                base_url=provider.base_url,
                                api_key=provider.api_key,
                                api_token=provider.api_token,
                                username=provider.username,
                                organization_id=provider.organization_id,
                                workspace_id=provider.workspace_id,
                                is_active=True,
                                test_connection=True,
                            )
                            if sync_result.get("success"):
                                results["synced"] += 1
                                if sync_result.get("connection_healthy"):
                                    results["healthy"] += 1
                                else:
                                    results["unhealthy"] += 1
                        except MCPSyncError as e:
                            results["unhealthy"] += 1
                            results["errors"].append(f"Provider {provider.id}: {e}")
            
            db.commit()
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"[MCPSync] Check and sync error: {e}", exc_info=True)
        results["errors"].append(str(e))
    
    return results

