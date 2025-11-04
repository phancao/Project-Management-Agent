"""
PM Provider Builder

Factory to create and configure PM provider instances based on configuration.
"""
from src.config.tools import PMProvider, SELECTED_PM_PROVIDER
from .base import BasePMProvider
from .models import PMProviderConfig
from .internal import InternalPMProvider
from .openproject import OpenProjectProvider
from .jira import JIRAProvider
from .clickup import ClickUpProvider
from sqlalchemy.orm import Session
from typing import Optional


def build_pm_provider(
    db_session: Optional[Session] = None
) -> Optional[BasePMProvider]:
    """
    Build a PM provider instance based on configuration
    
    Args:
        db_session: Database session for internal provider
        
    Returns:
        Configured PM provider instance or None if not configured
    """
    provider_type = SELECTED_PM_PROVIDER
    
    if not provider_type or provider_type == PMProvider.INTERNAL.value:
        # Use internal database
        if not db_session:
            return None
        config = PMProviderConfig(
            provider_type="internal",
            base_url=""
        )
        return InternalPMProvider(config, db_session)
    
    elif provider_type == PMProvider.OPENPROJECT.value:
        config = PMProviderConfig(
            provider_type="openproject",
            base_url=_get_env("OPENPROJECT_URL"),
            api_key=_get_env("OPENPROJECT_API_KEY")
        )
        return OpenProjectProvider(config)
    
    elif provider_type == PMProvider.JIRA.value:
        config = PMProviderConfig(
            provider_type="jira",
            base_url=_get_env("JIRA_URL"),
            api_token=_get_env("JIRA_API_TOKEN"),
            username=_get_env("JIRA_USERNAME")
        )
        return JIRAProvider(config)
    
    elif provider_type == PMProvider.CLICKUP.value:
        config = PMProviderConfig(
            provider_type="clickup",
            base_url="https://api.clickup.com/api/v2",
            api_key=_get_env("CLICKUP_API_KEY"),
            organization_id=_get_env("CLICKUP_TEAM_ID")
        )
        return ClickUpProvider(config)
    
    else:
        raise ValueError(f"Unsupported PM provider: {provider_type}")


def build_pm_provider_from_config(
    config: PMProviderConfig, db_session: Optional[Session] = None
) -> Optional[BasePMProvider]:
    """
    Build a PM provider instance from a PMProviderConfig object.
    
    Args:
        config: PMProviderConfig with provider settings
        db_session: Database session for internal provider
        
    Returns:
        Configured PM provider instance or None if not configured
    """
    provider_type = config.provider_type.lower()
    
    if provider_type == "internal":
        if not db_session:
            return None
        return InternalPMProvider(config, db_session)
    
    elif provider_type == "openproject":
        return OpenProjectProvider(config)
    
    elif provider_type == "jira":
        return JIRAProvider(config)
    
    elif provider_type == "clickup":
        return ClickUpProvider(config)
    
    else:
        raise ValueError(f"Unsupported PM provider type: {provider_type}")


def _get_env(key: str) -> str:
    """Get environment variable or return empty string"""
    import os
    return os.getenv(key, "")

