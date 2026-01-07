# PM Service - Users Router
"""
API endpoints for user operations.
"""

import logging
import traceback
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from pm_service.database import get_db_session
from pm_service.handlers import PMHandler
from pm_service.models.responses import UserResponse, ListResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=ListResponse)
async def list_users(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    provider_id: Optional[str] = Query(None, description="Filter by provider ID"),
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
    # DEBUG: Log the request source
    stack = ''.join(traceback.format_stack()[-5:-1])
    logger.warning(f"[DEBUG] list_users called - project_id={project_id}, provider_id={provider_id}, limit={limit}")
    logger.warning(f"[DEBUG] Call stack:\n{stack}")
    
    handler = PMHandler(db)
    try:
        all_users = await handler.list_users(project_id=project_id, provider_id=provider_id)
    except PermissionError as e:
        # Convert PermissionError to HTTPException so it's properly returned to client
        raise HTTPException(
            status_code=403,
            detail=str(e)
        ) from e
    
    # Apply pagination
    total = len(all_users)
    paginated = all_users[offset:offset + limit]
    
    logger.warning(f"[DEBUG] list_users returning {len(paginated)} of {total} users")
    
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
    logger.info(f"[DEBUG] get_user called - user_id={user_id}")
    
    handler = PMHandler(db)
    user = await handler.get_user(user_id)
    
    if not user:
        logger.warning(f"[DEBUG] get_user - user not found: {user_id}")
        raise HTTPException(status_code=404, detail="User not found")
    
    logger.info(f"[DEBUG] get_user - found user: {user.get('name', 'unknown')}")
    return user

