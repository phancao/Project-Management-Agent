"""
Provider Sync API for MCP Server

This module provides endpoints for synchronizing provider configurations
from the Backend to the MCP Server. This ensures both services have
consistent provider configurations.

Sync is triggered when:
1. A new provider is created in Backend
2. A provider's API key/token is updated in Backend
3. A provider is deleted/deactivated in Backend
4. Manual sync is requested (e.g., after token expiration fix)

Authentication:
All endpoints require a valid MCP API key via X-MCP-API-Key header.
This ensures only authorized services (Backend) can sync providers.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field

from ..database.connection import get_mcp_db_session
from ..database.models import PMProviderConnection
from ..services.auth_service import AuthService
from pm_providers.factory import create_pm_provider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/providers", tags=["Provider Sync"])


async def require_auth(request: Request) -> str:
    """
    Dependency to require authentication for all provider sync endpoints.
    
    Returns:
        user_id from the authenticated request
        
    Raises:
        HTTPException 401 if not authenticated
    """
    user_id = await AuthService.extract_user_id(request, require_auth=True)
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide X-MCP-API-Key header."
        )
    return user_id


class ProviderSyncRequest(BaseModel):
    """Request to sync a provider from Backend to MCP Server."""
    
    # Provider identification
    backend_provider_id: str = Field(..., description="Provider ID from Backend database")
    name: str = Field(..., description="Provider display name")
    provider_type: str = Field(..., description="Provider type (openproject_v13, jira, clickup, etc.)")
    base_url: str = Field(..., description="Provider base URL")
    
    # Credentials (at least one required for most providers)
    api_key: Optional[str] = Field(None, description="API key (for OpenProject, ClickUp)")
    api_token: Optional[str] = Field(None, description="API token (for JIRA)")
    username: Optional[str] = Field(None, description="Username (for JIRA)")
    
    # Optional configuration
    organization_id: Optional[str] = Field(None, description="Organization/Team ID")
    workspace_id: Optional[str] = Field(None, description="Workspace ID")
    project_key: Optional[str] = Field(None, description="Default project key")
    
    # Sync options
    is_active: bool = Field(True, description="Whether provider is active")
    test_connection: bool = Field(True, description="Test connection before saving")


class ProviderSyncResponse(BaseModel):
    """Response from provider sync operation."""
    
    success: bool
    action: str  # "created", "updated", "deactivated"
    mcp_provider_id: str  # MCP Server's provider ID
    backend_provider_id: str  # Backend's provider ID (for reference)
    message: str
    connection_tested: bool = False
    connection_healthy: bool = False


class ProviderDeleteRequest(BaseModel):
    """Request to delete/deactivate a provider in MCP Server."""
    
    backend_provider_id: str = Field(..., description="Provider ID from Backend database")
    hard_delete: bool = Field(False, description="If True, delete provider. If False, just deactivate.")


class BulkSyncRequest(BaseModel):
    """Request to sync multiple providers at once."""
    
    providers: list[ProviderSyncRequest]
    delete_missing: bool = Field(False, description="Delete MCP providers not in the sync list")


class BulkSyncResponse(BaseModel):
    """Response from bulk sync operation."""
    
    success: bool
    total: int
    synced: int
    failed: int
    deleted: int
    results: list[ProviderSyncResponse]
    errors: list[str]


@router.post("/sync", response_model=ProviderSyncResponse)
async def sync_provider(
    request: ProviderSyncRequest,
    user_id: str = Depends(require_auth)
) -> ProviderSyncResponse:
    """
    Sync a provider from Backend to MCP Server.
    
    This endpoint:
    1. Finds existing provider by (base_url, provider_type) OR backend_provider_id
    2. If exists: Updates credentials and configuration
    3. If not: Creates new provider
    4. Optionally tests the connection
    5. Returns MCP provider_id for Backend to store
    
    This should be called by Backend whenever:
    - A new provider is configured
    - Provider credentials are updated
    - Provider is activated/deactivated
    """
    db = next(get_mcp_db_session())
    
    try:
        # First, try to find by backend_provider_id (stored in additional_config)
        existing = db.query(PMProviderConnection).filter(
            PMProviderConnection.additional_config.contains({"backend_provider_id": request.backend_provider_id})
        ).first()
        
        # If not found, try to match by base_url and provider_type
        if not existing:
            # Normalize base_url for comparison (remove trailing slash)
            normalized_url = request.base_url.rstrip('/')
            
            existing = db.query(PMProviderConnection).filter(
                PMProviderConnection.provider_type == request.provider_type,
                PMProviderConnection.base_url.in_([normalized_url, normalized_url + '/'])
            ).first()
        
        connection_tested = False
        connection_healthy = False
        
        if existing:
            # Update existing provider
            logger.info(f"[ProviderSync] Updating existing provider: {existing.id}")
            
            existing.name = request.name  # type: ignore
            existing.api_key = request.api_key  # type: ignore
            existing.api_token = request.api_token  # type: ignore
            existing.username = request.username  # type: ignore
            existing.organization_id = request.organization_id  # type: ignore
            existing.workspace_id = request.workspace_id  # type: ignore
            existing.project_key = request.project_key  # type: ignore
            existing.is_active = request.is_active  # type: ignore
            
            # Store backend_provider_id in dedicated column AND additional_config (for backward compat)
            existing.backend_provider_id = request.backend_provider_id  # type: ignore
            additional_config: dict = dict(existing.additional_config) if existing.additional_config else {}
            additional_config["backend_provider_id"] = request.backend_provider_id
            existing.additional_config = additional_config  # type: ignore
            
            # Test connection if requested
            if request.test_connection and request.is_active:
                connection_tested = True
                connection_healthy = await _test_provider_connection(existing)
                if not connection_healthy:
                    logger.warning(f"[ProviderSync] Connection test failed for provider {existing.id}")
            
            db.commit()
            
            return ProviderSyncResponse(
                success=True,
                action="updated",
                mcp_provider_id=str(existing.id),
                backend_provider_id=request.backend_provider_id,
                message=f"Provider updated successfully",
                connection_tested=connection_tested,
                connection_healthy=connection_healthy
            )
        else:
            # Create new provider
            logger.info(f"[ProviderSync] Creating new provider: {request.provider_type} at {request.base_url}")
            
            new_provider = PMProviderConnection(
                name=request.name,
                provider_type=request.provider_type,
                base_url=request.base_url.rstrip('/'),
                api_key=request.api_key,
                api_token=request.api_token,
                username=request.username,
                organization_id=request.organization_id,
                workspace_id=request.workspace_id,
                project_key=request.project_key,
                is_active=request.is_active,
                backend_provider_id=request.backend_provider_id,  # Dedicated column
                additional_config={"backend_provider_id": request.backend_provider_id}  # For backward compat
            )
            
            db.add(new_provider)
            db.flush()  # Get the ID
            
            # Test connection if requested
            if request.test_connection and request.is_active:
                connection_tested = True
                connection_healthy = await _test_provider_connection(new_provider)
                if not connection_healthy:
                    logger.warning(f"[ProviderSync] Connection test failed for new provider {new_provider.id}")
            
            db.commit()
            
            return ProviderSyncResponse(
                success=True,
                action="created",
                mcp_provider_id=str(new_provider.id),
                backend_provider_id=request.backend_provider_id,
                message=f"Provider created successfully",
                connection_tested=connection_tested,
                connection_healthy=connection_healthy
            )
            
    except Exception as e:
        db.rollback()
        logger.error(f"[ProviderSync] Error syncing provider: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync provider: {str(e)}"
        )
    finally:
        db.close()


@router.post("/sync/bulk", response_model=BulkSyncResponse)
async def bulk_sync_providers(
    request: BulkSyncRequest,
    user_id: str = Depends(require_auth)
) -> BulkSyncResponse:
    """
    Sync multiple providers at once.
    
    This is useful for initial sync or periodic reconciliation.
    """
    results = []
    errors = []
    synced = 0
    failed = 0
    deleted = 0
    
    # Track backend_provider_ids that were synced
    synced_backend_ids = set()
    
    for provider_request in request.providers:
        try:
            result = await sync_provider(provider_request)
            results.append(result)
            synced_backend_ids.add(provider_request.backend_provider_id)
            if result.success:
                synced += 1
            else:
                failed += 1
        except HTTPException as e:
            failed += 1
            errors.append(f"Provider {provider_request.backend_provider_id}: {e.detail}")
            results.append(ProviderSyncResponse(
                success=False,
                action="failed",
                mcp_provider_id="",
                backend_provider_id=provider_request.backend_provider_id,
                message=str(e.detail)
            ))
        except Exception as e:
            failed += 1
            errors.append(f"Provider {provider_request.backend_provider_id}: {str(e)}")
            results.append(ProviderSyncResponse(
                success=False,
                action="failed",
                mcp_provider_id="",
                backend_provider_id=provider_request.backend_provider_id,
                message=str(e)
            ))
    
    # Delete providers not in sync list if requested
    if request.delete_missing:
        db = next(get_mcp_db_session())
        try:
            # Find providers with backend_provider_id not in synced list
            all_providers = db.query(PMProviderConnection).filter(
                PMProviderConnection.additional_config.isnot(None)
            ).all()
            
            for provider in all_providers:
                config_dict = dict(provider.additional_config) if provider.additional_config else {}
                backend_id = config_dict.get("backend_provider_id")
                if backend_id and backend_id not in synced_backend_ids:
                    logger.info(f"[ProviderSync] Deactivating orphaned provider: {provider.id}")
                    provider.is_active = False  # type: ignore
                    deleted += 1
            
            db.commit()
        except Exception as e:
            logger.error(f"[ProviderSync] Error cleaning up orphaned providers: {e}")
            errors.append(f"Cleanup error: {str(e)}")
        finally:
            db.close()
    
    return BulkSyncResponse(
        success=failed == 0,
        total=len(request.providers),
        synced=synced,
        failed=failed,
        deleted=deleted,
        results=results,
        errors=errors
    )


@router.delete("/sync", response_model=ProviderSyncResponse)
async def delete_provider(
    request: ProviderDeleteRequest,
    user_id: str = Depends(require_auth)
) -> ProviderSyncResponse:
    """
    Delete or deactivate a provider in MCP Server.
    
    Called by Backend when a provider is deleted.
    """
    db = next(get_mcp_db_session())
    
    try:
        # Find by backend_provider_id
        existing = db.query(PMProviderConnection).filter(
            PMProviderConnection.additional_config.contains({"backend_provider_id": request.backend_provider_id})
        ).first()
        
        if not existing:
            return ProviderSyncResponse(
                success=True,
                action="not_found",
                mcp_provider_id="",
                backend_provider_id=request.backend_provider_id,
                message="Provider not found in MCP Server (already deleted or never synced)"
            )
        
        if request.hard_delete:
            db.delete(existing)
            action = "deleted"
            message = "Provider deleted from MCP Server"
        else:
            existing.is_active = False  # type: ignore
            action = "deactivated"
            message = "Provider deactivated in MCP Server"
        
        db.commit()
        
        return ProviderSyncResponse(
            success=True,
            action=action,
            mcp_provider_id=str(existing.id),
            backend_provider_id=request.backend_provider_id,
            message=message
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"[ProviderSync] Error deleting provider: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete provider: {str(e)}"
        )
    finally:
        db.close()


@router.get("/sync/status")
async def get_sync_status(user_id: str = Depends(require_auth)):
    """
    Get the current sync status of all providers.
    
    Returns providers with their backend_provider_id mapping.
    """
    db = next(get_mcp_db_session())
    
    try:
        providers = db.query(PMProviderConnection).all()
        
        return {
            "total_providers": len(providers),
            "active_providers": sum(1 for p in providers if p.is_active),
            "providers": [
                {
                    "mcp_provider_id": str(p.id),
                    "backend_provider_id": (p.additional_config or {}).get("backend_provider_id"),
                    "name": p.name,
                    "provider_type": p.provider_type,
                    "base_url": p.base_url,
                    "is_active": p.is_active,
                    "has_api_key": bool(p.api_key),
                    "has_api_token": bool(p.api_token),
                    "synced": bool((p.additional_config or {}).get("backend_provider_id"))
                }
                for p in providers
            ]
        }
        
    finally:
        db.close()


@router.post("/sync/test/{mcp_provider_id}")
async def test_provider_connection(
    mcp_provider_id: str,
    user_id: str = Depends(require_auth)
):
    """
    Test connection for a specific provider.
    
    Useful for verifying credentials after sync.
    """
    db = next(get_mcp_db_session())
    
    try:
        try:
            provider_uuid = UUID(mcp_provider_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid provider ID format")
        
        provider = db.query(PMProviderConnection).filter(
            PMProviderConnection.id == provider_uuid
        ).first()
        
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        is_healthy = await _test_provider_connection(provider)
        
        return {
            "mcp_provider_id": mcp_provider_id,
            "provider_type": provider.provider_type,
            "base_url": provider.base_url,
            "connection_healthy": is_healthy,
            "message": "Connection successful" if is_healthy else "Connection failed"
        }
        
    finally:
        db.close()


async def _test_provider_connection(provider: PMProviderConnection) -> bool:
    """
    Test if a provider connection is healthy.
    
    Returns True if connection works, False otherwise.
    """
    try:
        # Create provider instance
        provider_instance = create_pm_provider(
            provider_type=str(provider.provider_type),
            base_url=str(provider.base_url),
            api_key=str(provider.api_key) if provider.api_key else None,
            api_token=str(provider.api_token) if provider.api_token else None,
            username=str(provider.username) if provider.username else None,
            organization_id=str(provider.organization_id) if provider.organization_id else None,
            workspace_id=str(provider.workspace_id) if provider.workspace_id else None,
        )
        
        # Try to list projects (simple operation to test connection)
        projects = await provider_instance.list_projects()
        
        logger.info(f"[ProviderSync] Connection test successful for {provider.id}: {len(projects)} projects found")
        return True
        
    except Exception as e:
        logger.warning(f"[ProviderSync] Connection test failed for {provider.id}: {e}")
        return False

