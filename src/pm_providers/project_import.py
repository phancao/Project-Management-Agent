"""
Project Import Service

Handles importing projects from PM providers (JIRA, OpenProject, etc.) 
into our internal database and creating sync mappings.
"""
import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from datetime import datetime

from .base import BasePMProvider
from .models import PMProviderConfig, PMProject
from .builder import build_pm_provider_from_config
from database import crud
from database.orm_models import Project, ProjectSyncMapping, PMProviderConnection

logger = logging.getLogger(__name__)


class ProjectImportResult:
    """Result of a project import operation"""
    def __init__(self):
        self.total_projects: int = 0
        self.imported: int = 0
        self.skipped: int = 0
        self.errors: List[Dict[str, str]] = []
        self.project_mappings: List[Dict[str, Any]] = []


async def import_projects_from_provider(
    provider: BasePMProvider,
    user_id: UUID,
    provider_connection_id: Optional[UUID] = None,
    db_session: Session = None,
    import_options: Optional[Dict[str, Any]] = None
) -> ProjectImportResult:
    """
    Import projects from a PM provider into our internal database.
    
    Args:
        provider: Initialized PM provider instance
        user_id: ID of the user performing the import
        provider_connection_id: Optional ID of provider connection record
        db_session: Database session
        import_options: Optional import configuration (e.g., skip_existing, project_filter)
        
    Returns:
        ProjectImportResult with import statistics
    """
    result = ProjectImportResult()
    import_options = import_options or {}
    skip_existing = import_options.get("skip_existing", True)
    project_filter = import_options.get("project_filter", None)  # Optional filter by name/pattern
    
    try:
        # Fetch projects from provider
        logger.info(f"Fetching projects from provider: {provider.config.provider_type}")
        provider_projects = await provider.list_projects()
        result.total_projects = len(provider_projects)
        
        logger.info(f"Found {result.total_projects} projects to import")
        
        # If we need to create/update provider connection record
        if provider_connection_id is None:
            # Try to find or create provider connection
            provider_connection_id = _get_or_create_provider_connection(
                db_session, provider, user_id
            )
        
        # Import each project
        for pm_project in provider_projects:
            try:
                # Apply filter if specified
                if project_filter and project_filter.lower() not in pm_project.name.lower():
                    result.skipped += 1
                    continue
                
                # Check if project already exists (by external ID)
                existing_mapping = None
                if provider_connection_id:
                    existing_mapping = db_session.query(ProjectSyncMapping).filter(
                        ProjectSyncMapping.provider_connection_id == provider_connection_id,
                        ProjectSyncMapping.external_project_id == str(pm_project.id)
                    ).first()
                
                if existing_mapping and skip_existing:
                    logger.info(f"Skipping existing project: {pm_project.name} (ID: {pm_project.id})")
                    result.skipped += 1
                    continue
                
                # Create or update internal project
                if existing_mapping:
                    # Update existing project
                    internal_project = crud.get_project(db_session, existing_mapping.internal_project_id)
                    if internal_project:
                        crud.update_project(
                            db_session,
                            existing_mapping.internal_project_id,
                            name=pm_project.name,
                            description=pm_project.description or "",
                            status=_map_provider_status(pm_project.status),
                            priority=_map_provider_priority(pm_project.priority)
                        )
                        project_id = existing_mapping.internal_project_id
                    else:
                        # Mapping exists but project was deleted, create new one
                        project_id = _create_internal_project(db_session, pm_project, user_id)
                else:
                    # Create new project
                    project_id = _create_internal_project(db_session, pm_project, user_id)
                
                # Commit after each successful project creation/update
                db_session.commit()
                
                # Create or update sync mapping
                if provider_connection_id:
                    if existing_mapping:
                        existing_mapping.last_sync_at = datetime.utcnow()
                        existing_mapping.sync_enabled = True
                        db_session.commit()
                    else:
                        mapping = ProjectSyncMapping(
                            internal_project_id=project_id,
                            provider_connection_id=provider_connection_id,
                            external_project_id=str(pm_project.id),
                            sync_enabled=True,
                            last_sync_at=datetime.utcnow(),
                            sync_config={
                                "auto_sync": import_options.get("auto_sync", False),
                                "sync_direction": "provider_to_internal"
                            }
                        )
                        db_session.add(mapping)
                        db_session.commit()
                
                result.imported += 1
                result.project_mappings.append({
                    "internal_project_id": str(project_id),
                    "external_project_id": str(pm_project.id),
                    "project_name": pm_project.name
                })
                
                logger.info(f"Imported project: {pm_project.name} (External ID: {pm_project.id})")
                
            except Exception as e:
                # Rollback transaction on error
                db_session.rollback()
                error_msg = f"Failed to import project '{pm_project.name}': {str(e)}"
                logger.error(error_msg, exc_info=True)
                result.errors.append({
                    "project_name": pm_project.name,
                    "external_project_id": str(pm_project.id),
                    "error": str(e)
                })
                result.skipped += 1
        
        logger.info(
            f"Import completed: {result.imported} imported, "
            f"{result.skipped} skipped, {len(result.errors)} errors"
        )
        
    except Exception as e:
        error_msg = f"Failed to fetch projects from provider: {str(e)}"
        logger.error(error_msg, exc_info=True)
        result.errors.append({
            "project_name": "ALL",
            "external_project_id": None,
            "error": error_msg
        })
    
    return result


def _create_internal_project(
    db_session: Session,
    pm_project: PMProject,
    user_id: UUID
) -> UUID:
    """Create an internal project from a PM provider project"""
    project = crud.create_project(
        db_session,
        name=pm_project.name,
        description=pm_project.description or "",
        created_by=user_id,
        domain=None,
        priority=_map_provider_priority(pm_project.priority),
        timeline_weeks=None,  # Could extract from dates if available
        budget=None
    )
    # Update status after creation (create_project sets default status)
    if pm_project.status:
        crud.update_project(
            db_session,
            project.id,
            status=_map_provider_status(pm_project.status)
        )
    return project.id


def _map_provider_status(provider_status: Optional[str]) -> str:
    """Map provider-specific status to internal status"""
    if not provider_status:
        return "planning"
    
    status_lower = provider_status.lower()
    
    # Common mappings
    if "active" in status_lower or "open" in status_lower or "in progress" in status_lower:
        return "active"
    elif "completed" in status_lower or "done" in status_lower or "closed" in status_lower:
        return "completed"
    elif "on hold" in status_lower or "paused" in status_lower:
        return "on_hold"
    elif "cancelled" in status_lower or "cancelled" in status_lower:
        return "cancelled"
    else:
        return "planning"


def _map_provider_priority(provider_priority: Optional[str]) -> str:
    """Map provider-specific priority to internal priority"""
    if not provider_priority:
        return "medium"
    
    priority_lower = provider_priority.lower()
    
    if "highest" in priority_lower or "critical" in priority_lower or "blocker" in priority_lower:
        return "high"
    elif "high" in priority_lower or "major" in priority_lower:
        return "high"
    elif "low" in priority_lower or "minor" in priority_lower or "trivial" in priority_lower:
        return "low"
    elif "lowest" in priority_lower:
        return "low"
    else:
        return "medium"


def _get_or_create_provider_connection(
    db_session: Session,
    provider: BasePMProvider,
    user_id: UUID
) -> Optional[UUID]:
    """Get or create a provider connection record"""
    try:
        # Try to find existing connection
        connection = db_session.query(PMProviderConnection).filter(
            PMProviderConnection.provider_type == provider.config.provider_type,
            PMProviderConnection.base_url == provider.config.base_url,
            PMProviderConnection.created_by == user_id
        ).first()
        
        if connection:
            connection.last_sync_at = datetime.utcnow()
            db_session.commit()
            return connection.id
        
        # Create new connection
        connection = PMProviderConnection(
            name=f"{provider.config.provider_type} - {provider.config.base_url}",
            provider_type=provider.config.provider_type,
            base_url=provider.config.base_url,
            api_key=provider.config.api_key,
            api_token=provider.config.api_token,
            username=provider.config.username,
            organization_id=provider.config.organization_id,
            workspace_id=provider.config.workspace_id,
            additional_config=provider.config.additional_config,
            is_active=True,
            created_by=user_id,
            last_sync_at=datetime.utcnow()
        )
        db_session.add(connection)
        db_session.commit()
        db_session.refresh(connection)
        return connection.id
        
    except Exception as e:
        logger.error(f"Failed to get/create provider connection: {e}", exc_info=True)
        return None


async def import_projects_from_config(
    config: PMProviderConfig,
    user_id: UUID,
    db_session: Session,
    import_options: Optional[Dict[str, Any]] = None
) -> ProjectImportResult:
    """
    Import projects using a provider configuration.
    
    This is a convenience wrapper that builds the provider and imports projects.
    """
    try:
        provider = build_pm_provider_from_config(config)
        if not provider:
            raise ValueError(f"Failed to build provider for type: {config.provider_type}")
        
        return await import_projects_from_provider(
            provider=provider,
            user_id=user_id,
            db_session=db_session,
            import_options=import_options
        )
    except Exception as e:
        logger.error(f"Failed to import projects from config: {e}", exc_info=True)
        result = ProjectImportResult()
        result.errors.append({
            "project_name": "ALL",
            "external_project_id": None,
            "error": str(e)
        })
        return result
