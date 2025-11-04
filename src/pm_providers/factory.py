# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
PM Provider Factory

Factory function to create PM provider instances from configuration parameters.
"""
from typing import Optional
from .base import BasePMProvider
from .models import PMProviderConfig
from .openproject import OpenProjectProvider
from .jira import JIRAProvider
from .clickup import ClickUpProvider


def create_pm_provider(
    provider_type: str,
    base_url: str,
    api_key: Optional[str] = None,
    api_token: Optional[str] = None,
    username: Optional[str] = None,
    organization_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
) -> BasePMProvider:
    """
    Create a PM provider instance from configuration parameters.
    
    Args:
        provider_type: Type of provider (openproject, jira, clickup)
        base_url: Base URL of the provider API
        api_key: API key (for OpenProject, ClickUp)
        api_token: API token (for JIRA)
        username: Username (for JIRA, should be email)
        organization_id: Organization/Team ID (for ClickUp)
        workspace_id: Workspace ID (for ClickUp)
        
    Returns:
        Configured PM provider instance
        
    Raises:
        ValueError: If provider_type is unsupported or required parameters are missing
    """
    config = PMProviderConfig(
        provider_type=provider_type,
        base_url=base_url,
        api_key=api_key,
        api_token=api_token,
        username=username,
        organization_id=organization_id,
        workspace_id=workspace_id,
    )
    
    if provider_type == "openproject":
        return OpenProjectProvider(config)
    elif provider_type == "jira":
        return JIRAProvider(config)
    elif provider_type == "clickup":
        return ClickUpProvider(config)
    else:
        raise ValueError(f"Unsupported provider type: {provider_type}")
