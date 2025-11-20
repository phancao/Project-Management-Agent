# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
PM Provider Factory

Factory function to create PM provider instances from configuration parameters.
"""
import os
import logging
from typing import Optional
from urllib.parse import urlparse, urlunparse
from .base import BasePMProvider
from .models import PMProviderConfig
from .openproject import OpenProjectProvider
from .openproject_v13 import OpenProjectV13Provider
from .jira import JIRAProvider
from .clickup import ClickUpProvider

logger = logging.getLogger(__name__)


def _is_running_in_docker() -> bool:
    """
    Detect if code is running inside a Docker container.
    
    Returns:
        True if running in Docker, False otherwise
    """
    # Check for Docker-specific files
    if os.path.exists("/.dockerenv"):
        return True
    
    # Check cgroup (more reliable)
    try:
        with open("/proc/self/cgroup", "r") as f:
            content = f.read()
            if "docker" in content or "containerd" in content:
                return True
    except (FileNotFoundError, IOError):
        pass
    
    return False


def _convert_localhost_to_docker_service(base_url: str) -> str:
    """
    Convert localhost URLs to Docker service names when running in containers.
    
    This fixes connection issues where containers try to connect to localhost
    but need to use Docker service names instead.
    
    Args:
        base_url: Original base URL (may contain localhost)
        
    Returns:
        Converted URL with Docker service name if applicable
    """
    if not _is_running_in_docker():
        return base_url
    
    try:
        parsed = urlparse(base_url)
        hostname = parsed.hostname
        port = parsed.port
        
        # Map localhost:port to Docker service names
        # Based on docker-compose.yml service definitions
        docker_service_map = {
            8080: "openproject",      # OpenProject v16
            8081: "openproject_v13",   # OpenProject v13
        }
        
        if hostname in ("localhost", "127.0.0.1") and port in docker_service_map:
            service_name = docker_service_map[port]
            # Docker services expose port 80 internally
            new_parsed = parsed._replace(netloc=f"{service_name}:80")
            new_url = urlunparse(new_parsed)
            logger.info(
                f"Converting localhost URL to Docker service: "
                f"{base_url} -> {new_url}"
            )
            return new_url
    except Exception as e:
        logger.warning(f"Failed to convert localhost URL {base_url}: {e}")
    
    return base_url


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
        ValueError: If provider_type is unsupported or required parameters
            are missing
    """
    # Convert localhost URLs to Docker service names when running in containers
    converted_base_url = _convert_localhost_to_docker_service(base_url)
    
    config = PMProviderConfig(
        provider_type=provider_type,
        base_url=converted_base_url,
        api_key=api_key,
        api_token=api_token,
        username=username,
        organization_id=organization_id,
        workspace_id=workspace_id,
    )
    
    # Normalize provider type to lowercase for case-insensitive matching
    provider_type_lower = provider_type.lower().strip()
    
    if provider_type_lower == "openproject" or provider_type_lower == "openproject_v16":
        return OpenProjectProvider(config)
    elif provider_type_lower == "openproject_v13":
        return OpenProjectV13Provider(config)
    elif provider_type_lower == "jira":
        return JIRAProvider(config)
    elif provider_type_lower == "clickup":
        return ClickUpProvider(config)
    else:
        raise ValueError(
            f"Unsupported provider type: {provider_type} "
            f"(supported: openproject, openproject_v13, openproject_v16, jira, clickup)"
        )
