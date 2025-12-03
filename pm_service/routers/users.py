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
    limit: int = Query(500, ge=1, le=1000, description="Max items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db_session)
):
    """
    List users.
    
    The handler fetches ALL users from providers.
    This endpoint applies limit/offset for pagination.
    
    If permission errors occur, they are raised as HTTPException with 403 status
    so the client can properly handle and display them to the user.
    """
    handler = PMHandler(db)
    try:
        all_users = await handler.list_users(project_id=project_id)
    except PermissionError as e:
        # Convert PermissionError to HTTPException so it's properly returned to client
        raise HTTPException(
            status_code=403,
            detail=str(e)
        ) from e
    
    # Apply pagination
    total = len(all_users)
    paginated = all_users[offset:offset + limit]
    
    return ListResponse(
        items=paginated,
        total=total,
        returned=len(paginated),
        offset=offset,
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

