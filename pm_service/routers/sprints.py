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
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db_session)
):
    """List sprints."""
    handler = PMHandler(db)
    sprints = await handler.list_sprints(
        project_id=project_id,
        status=status,
        limit=limit
    )
    
    return ListResponse(
        items=sprints,
        total=len(sprints),
        returned=len(sprints),
        offset=0,
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
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db_session)
):
    """Get tasks in a sprint."""
    handler = PMHandler(db)
    tasks = await handler.list_tasks(sprint_id=sprint_id, limit=limit)
    
    return ListResponse(
        items=tasks,
        total=len(tasks),
        returned=len(tasks),
        offset=0,
        limit=limit
    )

