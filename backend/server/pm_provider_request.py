# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from typing import Optional
from pydantic import BaseModel, Field


class ProjectImportRequest(BaseModel):
    """Request model for importing projects from a provider"""
    provider_type: str = Field(
        ..., description="Provider type: openproject, jira, clickup"
    )
    base_url: str = Field(..., description="Provider base URL/IP")
    api_key: Optional[str] = Field(
        None, description="API key (for OpenProject, ClickUp)"
    )
    api_token: Optional[str] = Field(None, description="API token (for JIRA)")
    username: Optional[str] = Field(
        None,
        description=(
            "Username. For JIRA Cloud, use your email address "
            "(e.g., user@example.com)"
        ),
    )
    organization_id: Optional[str] = Field(
        None, description="Organization/Team ID"
    )
    workspace_id: Optional[str] = Field(None, description="Workspace ID")
    import_options: Optional[dict] = Field(None, description="Import options")


class ProviderUpdateRequest(BaseModel):
    """Request model for updating a provider"""
    provider_type: Optional[str] = Field(None, description="Provider type")
    base_url: Optional[str] = Field(None, description="Provider base URL")
    api_key: Optional[str] = Field(None, description="API key")
    api_token: Optional[str] = Field(None, description="API token")
    username: Optional[str] = Field(None, description="Username")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    workspace_id: Optional[str] = Field(None, description="Workspace ID")
