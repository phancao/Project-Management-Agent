"""
PM Provider Builder

Factory to create and configure PM provider instances based on configuration.
"""
import os
from .base import BasePMProvider
from .models import PMProviderConfig
from .internal import InternalPMProvider
from .openproject import OpenProjectProvider
from .openproject_v13 import OpenProjectV13Provider
from .jira import JIRAProvider
from .clickup import ClickUpProvider
from sqlalchemy.orm import Session
from typing import Optional


def build_pm_provider(db_session: Optional[Session] = None) -> Optional[BasePMProvider]:
    """
    Build a PM provider instance based on configuration
    
    Args:
        db_session: Database session for internal provider
        
    Returns:
        Configured PM provider instance or None if not configured
    """
    provider_type = os.getenv("PM_PROVIDER", "internal")
    
    if not provider_type or provider_type == "internal":
        # Use internal database
        if not db_session:
            return None
        config = PMProviderConfig(
            provider_type="internal",
            base_url=""
        )
        return InternalPMProvider(config, db_session)
    
    elif provider_type == "openproject":
        # Check if v13 is specified via environment variable or use v16 by default
        openproject_version = _get_env("OPENPROJECT_VERSION")
        config = PMProviderConfig(
            provider_type="openproject",
            base_url=_get_env("OPENPROJECT_URL"),
            api_key=_get_env("OPENPROJECT_API_KEY")
        )
        if openproject_version and openproject_version.lower() == "13":
            return OpenProjectV13Provider(config)
        else:
            return OpenProjectProvider(config)
    
    elif provider_type == "jira":
        config = PMProviderConfig(
            provider_type="jira",
            base_url=_get_env("JIRA_URL"),
            api_token=_get_env("JIRA_API_TOKEN"),
            username=_get_env("JIRA_USERNAME")
        )
        return JIRAProvider(config)
    
    elif provider_type == "clickup":
        config = PMProviderConfig(
            provider_type="clickup",
            base_url="https://api.clickup.com/api/v2",
            api_key=_get_env("CLICKUP_API_KEY"),
            organization_id=_get_env("CLICKUP_TEAM_ID")
        )
        return ClickUpProvider(config)
    
    else:
        raise ValueError(f"Unsupported PM provider: {provider_type}")


def _get_env(key: str) -> str:
    """Get environment variable or return empty string"""
    import os
    return os.getenv(key, "")

