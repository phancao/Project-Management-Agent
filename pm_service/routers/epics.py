# PM Service - Epics Router
"""
API endpoints for epic operations.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from pm_service.database import get_db_session
from pm_service.handlers import PMHandler
from pm_service.models.responses import ListResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/epics", tags=["epics"])


class EpicCreate(BaseModel):
    """Epic creation request."""
    project_id: str
    name: str
    description: Optional[str] = None
    color: Optional[str] = None


class EpicUpdate(BaseModel):
    """Epic update request."""
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None


@router.get("", response_model=ListResponse)
async def list_epics(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    limit: int = Query(500, ge=1, le=1000, description="Max items to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db_session)
):
    """
    List all epics.
    
    The handler fetches ALL epics from providers.
    This endpoint applies limit/offset for pagination.
    """
    handler = PMHandler(db)
    
    try:
        all_epics = await handler.list_epics(project_id=project_id)
        
        # Apply pagination
        total = len(all_epics)
        paginated = all_epics[offset:offset + limit]
        
        return ListResponse(
            items=paginated,
            total=total,
            returned=len(paginated),
            offset=offset,
            limit=limit
        )
    except Exception as e:
        logger.error(f"Error listing epics: {e}")
        return ListResponse(
            items=[],
            total=0,
            returned=0,
            offset=offset,
            limit=limit
        )


@router.get("/{epic_id}")
async def get_epic(
    epic_id: str,
    db: Session = Depends(get_db_session)
):
    """Get epic by ID."""
    handler = PMHandler(db)
    epic = await handler.get_epic(epic_id)
    
    if not epic:
        raise HTTPException(status_code=404, detail="Epic not found")
    
    return epic


@router.post("")
async def create_epic(
    data: EpicCreate,
    db: Session = Depends(get_db_session)
):
    """Create a new epic."""
    handler = PMHandler(db)
    
    try:
        epic = await handler.create_epic(
            project_id=data.project_id,
            name=data.name,
            description=data.description,
            color=data.color
        )
        
        if not epic:
            raise HTTPException(status_code=500, detail="Failed to create epic")
        
        return epic
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating epic: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{epic_id}")
async def update_epic(
    epic_id: str,
    data: EpicUpdate,
    db: Session = Depends(get_db_session)
):
    """Update an epic."""
    handler = PMHandler(db)
    
    try:
        updates = data.model_dump(exclude_none=True)
        epic = await handler.update_epic(epic_id, **updates)
        
        if not epic:
            raise HTTPException(status_code=404, detail="Epic not found")
        
        return epic
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating epic: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{epic_id}")
async def delete_epic(
    epic_id: str,
    db: Session = Depends(get_db_session)
):
    """Delete an epic."""
    handler = PMHandler(db)
    
    try:
        success = await handler.delete_epic(epic_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Epic not found")
        
        return {"status": "deleted", "id": epic_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting epic: {e}")
        raise HTTPException(status_code=500, detail=str(e))

