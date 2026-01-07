# PM Service - Tasks Router
"""
API endpoints for task operations.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from pm_service.database import get_db_session
from pm_service.handlers import PMHandler
from pm_service.models.requests import CreateTaskRequest, UpdateTaskRequest
from pm_service.models.responses import TaskResponse, ListResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=ListResponse)
async def list_tasks(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    sprint_id: Optional[str] = Query(None, description="Filter by sprint ID"),
    assignee_id: Optional[str] = Query(None, description="Filter by assignee ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    provider_id: Optional[str] = Query(None, description="Filter by provider ID"),
    limit: Optional[int] = Query(None, ge=1, description="Max items to return (unlimited if not specified)"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db_session)
):
    """
    List tasks with filters and pagination.
    
    The handler fetches ALL tasks from providers (providers handle their own pagination).
    This endpoint then applies limit/offset for API-level pagination if specified.
    """
    # DEBUG: Log the request with all parameters
    logger.warning(f"[DEBUG] list_tasks called - assignee_id={assignee_id}, status={status}, project_id={project_id}, limit={limit}")
    
    handler = PMHandler(db)
    
    # Handler returns ALL matching tasks (no internal limit)
    all_tasks = await handler.list_tasks(
        project_id=project_id,
        sprint_id=sprint_id,
        assignee_id=assignee_id,
        status=status,
        provider_id=provider_id,
    )
    
    # Apply pagination at API level only if limit is specified
    total = len(all_tasks)
    if limit is not None:
        paginated_tasks = all_tasks[offset:offset + limit]
    else:
        paginated_tasks = all_tasks[offset:] if offset > 0 else all_tasks
    
    logger.warning(f"[DEBUG] list_tasks returning {len(paginated_tasks)} of {total} tasks for assignee={assignee_id}")
    
    return ListResponse(
        items=paginated_tasks,
        total=total,
        returned=len(paginated_tasks),
        offset=offset,
        limit=limit if limit is not None else total
    )


@router.get("/{task_id}")
async def get_task(
    task_id: str,
    db: Session = Depends(get_db_session)
):
    """Get all tasks."""
    handler = PMHandler(db)
    task = await handler.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task


@router.post("")
async def create_task(
    request: CreateTaskRequest,
    db: Session = Depends(get_db_session)
):
    """Create a new task."""
    handler = PMHandler(db)
    
    try:
        task = await handler.create_task(
            project_id=request.project_id,
            title=request.title,
            description=request.description,
            assignee_id=request.assignee_id,
            sprint_id=request.sprint_id,
            story_points=request.story_points,
            priority=request.priority,
            task_type=request.task_type,
            parent_id=request.parent_id
        )
        
        if not task:
            raise HTTPException(status_code=500, detail="Failed to create task")
        
        return task
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{task_id}")
async def update_task(
    task_id: str,
    request: UpdateTaskRequest,
    db: Session = Depends(get_db_session)
):
    """Update a task."""
    handler = PMHandler(db)
    
    try:
        updates = request.model_dump(exclude_unset=True)
        task = await handler.update_task(task_id, **updates)
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return task
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

