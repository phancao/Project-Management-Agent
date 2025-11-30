# PM Service - Providers Router
"""
API endpoints for provider management.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from pm_service.database import get_db_session
from pm_service.database.models import PMProviderConnection
from pm_service.handlers import PMHandler
from pm_service.models.requests import ProviderSyncRequest
from pm_service.models.responses import ProviderResponse, ListResponse

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("", response_model=ListResponse)
async def list_providers(
    db: Session = Depends(get_db_session)
):
    """List all configured providers."""
    handler = PMHandler(db)
    providers = handler.get_active_providers()
    
    items = [
        ProviderResponse(
            id=str(p.id),
            name=p.name,
            provider_type=p.provider_type,
            base_url=p.base_url,
            is_active=p.is_active,
            is_connected=True,  # TODO: actual connection check
            last_sync_at=p.last_sync_at
        )
        for p in providers
    ]
    
    return ListResponse(
        items=[item.model_dump() for item in items],
        total=len(items),
        returned=len(items),
        offset=0,
        limit=100
    )


@router.get("/{provider_id}")
async def get_provider(
    provider_id: str,
    db: Session = Depends(get_db_session)
):
    """Get provider by ID."""
    handler = PMHandler(db)
    provider = handler.get_provider_by_id(provider_id)
    
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    return ProviderResponse(
        id=str(provider.id),
        name=provider.name,
        provider_type=provider.provider_type,
        base_url=provider.base_url,
        is_active=provider.is_active,
        is_connected=True,
        last_sync_at=provider.last_sync_at
    )


@router.post("/sync")
async def sync_provider(
    request: ProviderSyncRequest,
    db: Session = Depends(get_db_session)
):
    """Sync provider configuration from backend."""
    # Check if provider already exists by backend_provider_id
    existing = db.query(PMProviderConnection).filter(
        PMProviderConnection.backend_provider_id == UUID(request.backend_provider_id)
    ).first()
    
    if existing:
        # Update existing provider
        existing.name = request.name
        existing.provider_type = request.provider_type
        existing.base_url = request.base_url
        existing.api_key = request.api_key
        existing.api_token = request.api_token
        existing.username = request.username
        existing.is_active = request.is_active
        existing.additional_config = request.additional_config
        existing.last_sync_at = datetime.utcnow()
        existing.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(existing)
        
        return {
            "status": "updated",
            "provider_id": str(existing.id),
            "backend_provider_id": request.backend_provider_id
        }
    else:
        # Create new provider
        new_provider = PMProviderConnection(
            name=request.name,
            provider_type=request.provider_type,
            base_url=request.base_url,
            api_key=request.api_key,
            api_token=request.api_token,
            username=request.username,
            is_active=request.is_active,
            backend_provider_id=UUID(request.backend_provider_id),
            additional_config=request.additional_config,
            last_sync_at=datetime.utcnow()
        )
        
        db.add(new_provider)
        db.commit()
        db.refresh(new_provider)
        
        return {
            "status": "created",
            "provider_id": str(new_provider.id),
            "backend_provider_id": request.backend_provider_id
        }


@router.delete("/{provider_id}")
async def delete_provider(
    provider_id: str,
    db: Session = Depends(get_db_session)
):
    """Delete a provider."""
    provider = db.query(PMProviderConnection).filter(
        PMProviderConnection.id == provider_id
    ).first()
    
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    db.delete(provider)
    db.commit()
    
    return {"status": "deleted", "provider_id": provider_id}

