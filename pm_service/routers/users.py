# PM Service - Users Router
"""
API endpoints for user operations.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from pm_service.database import get_db_session
from pm_service.handlers import PMHandler
from pm_service.models.responses import UserResponse, ListResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=ListResponse)
async def list_users(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db_session)
):
    """List users."""
    handler = PMHandler(db)
    users = await handler.list_users(project_id=project_id, limit=limit)
    
    return ListResponse(
        items=users,
        total=len(users),
        returned=len(users),
        offset=0,
        limit=limit
    )


@router.get("/{user_id}")
async def get_user(
    user_id: str,
    db: Session = Depends(get_db_session)
):
    """Get user by ID."""
    handler = PMHandler(db)
    user = await handler.get_user(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

