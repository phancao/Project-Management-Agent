# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
PM Provider Factory

Factory function to create PM provider instances from configuration parameters.
"""
import os
import logging
import base64
import requests
from typing import Optional, Tuple
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


def detect_openproject_version(
    base_url: str,
    api_key: Optional[str] = None,
    api_token: Optional[str] = None
) -> Tuple[Optional[str], str]:
    """
    Detect OpenProject version from the /api/v3 root endpoint.
    
    The root endpoint returns a 'coreVersion' field (e.g., "13.4.0", "16.0.0")
    which we use to determine which provider implementation to use.
    
    Args:
        base_url: OpenProject base URL
        api_key: API key for authentication
        api_token: Alternative API token
        
    Returns:
        Tuple of (detected_version_string, recommended_provider_type)
        - detected_version_string: e.g., "13.4.0" or None if detection failed
        - recommended_provider_type: "openproject_v13" or "openproject_v16"
    """
    key = api_key or api_token
    if not key:
        logger.warning("No API key provided for OpenProject version detection, defaulting to v13")
        return (None, "openproject_v13")
    
    try:
        # Build authentication header
        auth_string = f"apikey:{key.strip()}"
        credentials = base64.b64encode(auth_string.encode()).decode()
        headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json"
        }
        
        # Query the root API endpoint
        resp = requests.get(f"{base_url}/api/v3", headers=headers, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            core_version = data.get("coreVersion")
            
            if core_version:
                logger.info(f"Detected OpenProject version: {core_version}")
                
                # Parse major version number
                try:
                    major_version = int(core_version.split(".")[0])
                    
                    # v14+ uses the newer API patterns (openproject_v16 provider)
                    # v13 and below use the older API patterns (openproject_v13 provider)
                    if major_version >= 14:
                        logger.info(f"OpenProject v{major_version} detected, using v16 provider")
                        return (core_version, "openproject_v16")
                    else:
                        logger.info(f"OpenProject v{major_version} detected, using v13 provider")
                        return (core_version, "openproject_v13")
                except (ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse version '{core_version}': {e}")
            else:
                logger.info("coreVersion not returned (may require admin privileges)")
        elif resp.status_code == 401:
            logger.warning("Authentication failed for version detection, defaulting to v13")
        else:
            logger.warning(f"Version detection request failed with status {resp.status_code}")
            
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout while detecting OpenProject version from {base_url}")
    except requests.exceptions.RequestException as e:
        logger.warning(f"Network error during OpenProject version detection: {e}")
    except Exception as e:
        logger.warning(f"Unexpected error during OpenProject version detection: {e}")
    
    # Default to v13 provider (more compatible, safer fallback)
    logger.info("Defaulting to OpenProject v13 provider")
    return (None, "openproject_v13")


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
            - "openproject": Auto-detect version and use appropriate provider
            - "openproject_v13": Force OpenProject v13 provider
            - "openproject_v16": Force OpenProject v16 provider
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
    
    # Normalize provider type to lowercase for case-insensitive matching
    provider_type_lower = provider_type.lower().strip()
    
    # Auto-detect OpenProject version when generic "openproject" type is specified
    if provider_type_lower == "openproject":
        detected_version, recommended_type = detect_openproject_version(
            converted_base_url, api_key, api_token
        )
        provider_type_lower = recommended_type
        logger.info(
            f"Auto-detected OpenProject provider type: {recommended_type} "
            f"(version: {detected_version or 'unknown'})"
        )
    
    config = PMProviderConfig(
        provider_type=provider_type_lower,
        base_url=converted_base_url,
        api_key=api_key,
        api_token=api_token,
        username=username,
        organization_id=organization_id,
        workspace_id=workspace_id,
    )
    
    if provider_type_lower == "openproject_v16":
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

