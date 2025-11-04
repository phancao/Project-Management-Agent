"""
Request and Response models for Project Import API
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID


class ProjectImportRequest(BaseModel):
    """Request model for importing projects from a provider"""
    provider_type: str = Field(..., description="Provider type: openproject, jira, clickup")
    base_url: str = Field(..., description="Provider base URL/IP")
    api_key: Optional[str] = Field(None, description="API key (for OpenProject, ClickUp)")
    api_token: Optional[str] = Field(None, description="API token (for JIRA)")
    username: Optional[str] = Field(
        None, 
        description="Username. For JIRA Cloud, use your email address (e.g., user@example.com)"
    )
    organization_id: Optional[str] = Field(None, description="Organization/Team ID")
    workspace_id: Optional[str] = Field(None, description="Workspace ID")
    additional_config: Optional[Dict[str, Any]] = Field(
        None, description="Additional provider-specific configuration"
    )
    import_options: Optional[Dict[str, Any]] = Field(
        None,
        description="Import options: skip_existing (bool), project_filter (str), auto_sync (bool)"
    )


class ProjectImportResponse(BaseModel):
    """Response model for provider configuration save operation"""
    success: bool = Field(..., description="Whether the provider config was saved")
    provider_config_id: Optional[str] = Field(None, description="Saved provider config ID")
    total_projects: int = Field(..., description="Total projects found in provider (for verification)")
    projects: List[Dict[str, Any]] = Field(
        default=[], description="List of projects found in provider (not saved)"
    )
    errors: List[Dict[str, Any]] = Field(
        default=[], description="List of errors encountered"
    )
    message: Optional[str] = Field(None, description="Status message")
