# PM Service - Projects Router
"""
API endpoints for project operations.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from pm_service.database import get_db_session
from pm_service.handlers import PMHandler
from pm_service.models.responses import ProjectResponse, ListResponse

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=ListResponse)
async def list_projects(
    provider_id: Optional[str] = Query(None, description="Filter by provider ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db_session)
):
    """List all projects."""
    handler = PMHandler(db, user_id=user_id)
    projects = await handler.list_projects(provider_id=provider_id, limit=limit)
    
    return ListResponse(
        items=projects[offset:offset + limit],
        total=len(projects),
        returned=min(len(projects) - offset, limit),
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

