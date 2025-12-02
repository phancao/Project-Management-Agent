# PM Service - Projects Router
"""
API endpoints for project operations.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from pm_service.database import get_db_session
from pm_service.handlers import PMHandler
from pm_service.models.responses import ProjectResponse, ListResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=ListResponse)
async def list_projects(
    provider_id: Optional[str] = Query(None, description="Filter by provider ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: int = Query(1000, ge=1, le=5000, description="Max items to return (default: 1000, max: 5000)"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db_session)
):
    """
    List all projects from all providers.
    
    The handler fetches ALL projects from providers.
    This endpoint applies limit/offset for pagination.
    """
    handler = PMHandler(db, user_id=user_id)
    
    # Handler returns ALL projects (no internal limit)
    all_projects = await handler.list_projects(provider_id=provider_id)
    
    # Apply pagination at API level
    total = len(all_projects)
    paginated_projects = all_projects[offset:offset + limit]
    
    return ListResponse(
        items=paginated_projects,
        total=total,
        returned=len(paginated_projects),
        offset=offset,
        limit=limit
    )


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    db: Session = Depends(get_db_session)
):
    """Get project by ID."""
    handler = PMHandler(db)
    project = await handler.get_project(project_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return project


@router.get("/{project_id}/statuses", response_model=ListResponse)
async def list_project_statuses(
    project_id: str,
    entity_type: str = Query("task", description="Entity type (task, sprint, etc.)"),
    db: Session = Depends(get_db_session)
):
    """List available statuses for a project."""
    handler = PMHandler(db)
    
    try:
        # Get provider for this project
        provider_id, actual_project_id = handler._parse_composite_id(project_id)
        
        if not provider_id:
            # Try to find from active providers
            providers = handler.get_active_providers()
            if not providers:
                return ListResponse(items=[], total=0, returned=0, offset=0, limit=100)
            provider_id = str(providers[0].id)
        
        provider = handler.get_provider(provider_id)
        if not provider:
            return ListResponse(items=[], total=0, returned=0, offset=0, limit=100)
        
        # Get statuses from provider
        if hasattr(provider, 'list_statuses'):
            statuses = await provider.list_statuses(project_id=actual_project_id, entity_type=entity_type)
        else:
            # Default statuses if provider doesn't support listing
            statuses = [
                {"id": "new", "name": "New", "color": "#808080"},
                {"id": "in_progress", "name": "In Progress", "color": "#0000FF"},
                {"id": "done", "name": "Done", "color": "#00FF00"},
            ]
        
        return ListResponse(
            items=statuses,
            total=len(statuses),
            returned=len(statuses),
            offset=0,
            limit=100
        )
    except Exception as e:
        logger.error(f"Error listing statuses for project {project_id}: {e}")
        # Return default statuses on error
        default_statuses = [
            {"id": "new", "name": "New", "color": "#808080"},
            {"id": "in_progress", "name": "In Progress", "color": "#0000FF"},
            {"id": "done", "name": "Done", "color": "#00FF00"},
        ]
        return ListResponse(
            items=default_statuses,
            total=len(default_statuses),
            returned=len(default_statuses),
            offset=0,
            limit=100
        )


@router.get("/{project_id}/priorities", response_model=ListResponse)
async def list_project_priorities(
    project_id: str,
    db: Session = Depends(get_db_session)
):
    """List available priorities for a project."""
    handler = PMHandler(db)
    
    try:
        # Get provider for this project
        provider_id, actual_project_id = handler._parse_composite_id(project_id)
        
        if not provider_id:
            providers = handler.get_active_providers()
            if not providers:
                return ListResponse(items=[], total=0, returned=0, offset=0, limit=100)
            provider_id = str(providers[0].id)
        
        provider = handler.get_provider(provider_id)
        if not provider:
            return ListResponse(items=[], total=0, returned=0, offset=0, limit=100)
        
        # Get priorities from provider
        if hasattr(provider, 'list_priorities'):
            priorities = await provider.list_priorities(project_id=actual_project_id)
        else:
            # Default priorities if provider doesn't support listing
            priorities = [
                {"id": "low", "name": "Low", "color": "#00FF00"},
                {"id": "normal", "name": "Normal", "color": "#808080"},
                {"id": "high", "name": "High", "color": "#FFA500"},
                {"id": "urgent", "name": "Urgent", "color": "#FF0000"},
            ]
        
        return ListResponse(
            items=priorities,
            total=len(priorities),
            returned=len(priorities),
            offset=0,
            limit=100
        )
    except Exception as e:
        logger.error(f"Error listing priorities for project {project_id}: {e}")
        # Return default priorities on error
        default_priorities = [
            {"id": "low", "name": "Low", "color": "#00FF00"},
            {"id": "normal", "name": "Normal", "color": "#808080"},
            {"id": "high", "name": "High", "color": "#FFA500"},
            {"id": "urgent", "name": "Urgent", "color": "#FF0000"},
        ]
        return ListResponse(
            items=default_priorities,
            total=len(default_priorities),
            returned=len(default_priorities),
            offset=0,
            limit=100
        )

