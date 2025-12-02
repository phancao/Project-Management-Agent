# PM Service - Sprints Router
"""
API endpoints for sprint operations.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from pm_service.database import get_db_session
from pm_service.handlers import PMHandler
from pm_service.models.responses import SprintResponse, ListResponse

router = APIRouter(prefix="/sprints", tags=["sprints"])


@router.get("", response_model=ListResponse)
async def list_sprints(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    status: Optional[str] = Query(None, description="Filter by status (active, closed, future)"),
    limit: int = Query(500, ge=1, le=1000, description="Max items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db_session)
):
    """
    List sprints.
    
    The handler fetches ALL sprints from providers.
    This endpoint applies limit/offset for pagination.
    """
    handler = PMHandler(db)
    all_sprints = await handler.list_sprints(
        project_id=project_id,
        status=status
    )
    
    # Apply pagination
    total = len(all_sprints)
    paginated = all_sprints[offset:offset + limit]
    
    return ListResponse(
        items=paginated,
        total=total,
        returned=len(paginated),
        offset=offset,
        limit=limit
    )


@router.get("/{sprint_id}")
async def get_sprint(
    sprint_id: str,
    db: Session = Depends(get_db_session)
):
    """Get sprint by ID."""
    handler = PMHandler(db)
    sprint = await handler.get_sprint(sprint_id)
    
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    
    return sprint


@router.get("/{sprint_id}/tasks", response_model=ListResponse)
async def get_sprint_tasks(
    sprint_id: str,
    limit: int = Query(500, ge=1, le=1000, description="Max items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db_session)
):
    """
    Get tasks in a sprint.
    
    The handler fetches ALL tasks from providers.
    This endpoint applies limit/offset for pagination.
    """
    handler = PMHandler(db)
    all_tasks = await handler.list_tasks(sprint_id=sprint_id)
    
    # Apply pagination
    total = len(all_tasks)
    paginated = all_tasks[offset:offset + limit]
    
    return ListResponse(
        items=paginated,
        total=total,
        returned=len(paginated),
        offset=offset,
        limit=limit
    )

