# PM Service - Time Entries Router
"""
API endpoints for time entry operations.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session

from pm_service.database import get_db_session
from pm_service.handlers import PMHandler
from pm_service.models.requests import LogTimeRequest
from pm_service.models.responses import ListResponse

router = APIRouter(prefix="/time_entries", tags=["time_entries"])


@router.get("", response_model=ListResponse)
async def list_time_entries(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    task_id: Optional[str] = Query(None, description="Filter by task ID"),
    start_date: Optional[str] = Query(None, description="Filter by start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter by end date (YYYY-MM-DD)"),
    provider_id: Optional[str] = Query(None, description="Filter by provider ID"),
    limit: int = Query(100, ge=1, le=5000, description="Max items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db_session)
):
    """
    List time entries with filters.
    """
    handler = PMHandler(db)
    
    entries = await handler.list_time_entries(
        project_id=project_id,
        user_id=user_id,
        task_id=task_id,
        start_date=start_date,
        end_date=end_date,
        provider_id=provider_id
    )
    
    # Pagination
    total = len(entries)
    paginated = entries[offset:offset + limit]
    
    return ListResponse(
        items=paginated,
        total=total,
        returned=len(paginated),
        offset=offset,
        limit=limit
    )


@router.post("")
async def log_time_entry(
    task_id: str = Query(..., description="Task ID to log time for"),
    request: LogTimeRequest = Body(...),
    db: Session = Depends(get_db_session)
):
    """
    Log time entry for a task.
    
    Requires task_id as query parameter.
    """
    handler = PMHandler(db)
    
    try:
        entry = await handler.log_time_entry(
            task_id=task_id,
            hours=request.hours,
            comment=request.comment,
            activity_id=request.activity_type
        )
        
        if not entry:
            raise HTTPException(status_code=500, detail="Failed to log time entry")
            
        return entry
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
