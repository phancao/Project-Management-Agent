"""
PM MCP Tools for DeerFlow Agents

This module provides PM tools via MCP client, allowing agents to connect
to the PM MCP Server instead of using direct PMHandler integration.

This approach offers several advantages:
- Centralized PM operations through MCP server
- Support for multiple agents (QC, HR, etc.)
- Better separation of concerns
- Easier testing and monitoring
"""

import logging
from typing import Optional

from langchain_mcp_adapters.client import MultiServerMCPClient

logger = logging.getLogger(__name__)


# Global MCP client instance
_mcp_client: Optional[MultiServerMCPClient] = None
_pm_mcp_config: Optional[dict] = None


def configure_pm_mcp_client(
    transport: str = "sse",
    url: str = "http://localhost:8080",
    enabled_tools: Optional[list[str]] = None
) -> None:
    """
    Configure the PM MCP client for DeerFlow agents.
    
    Args:
        transport: Transport type ("sse" or "stdio")
        url: MCP server URL (for SSE transport)
        enabled_tools: List of specific tools to enable (None = all tools)
    
    Example:
        # Enable all PM tools via SSE
        configure_pm_mcp_client(
            transport="sse",
            url="http://localhost:8080"
        )
        
        # Enable specific tools only
        configure_pm_mcp_client(
            transport="sse",
            url="http://localhost:8080",
            enabled_tools=["list_projects", "list_my_tasks", "get_project"]
        )
    """
    global _pm_mcp_config
    
    _pm_mcp_config = {
        "pm-server": {
            "transport": transport,
            "url": url if transport == "sse" else None,
            "enabled_tools": enabled_tools,
        }
    }
    
    logger.info(
        f"PM MCP client configured: transport={transport}, "
        f"url={url}, enabled_tools={len(enabled_tools) if enabled_tools else 'all'}"
    )


async def get_pm_mcp_tools() -> list:
    """
    Get PM tools from MCP server.
    
    This function connects to the PM MCP Server and loads all available
    PM tools that can be used by DeerFlow agents.
    
    Returns:
        List of LangChain tools loaded from PM MCP Server
        
    Raises:
        RuntimeError: If PM MCP client is not configured
        
    Example:
        # Configure and get tools
        configure_pm_mcp_client(transport="sse", url="http://localhost:8080")
        pm_tools = await get_pm_mcp_tools()
        
        # Use in agent
        agent = create_agent("researcher", pm_tools)
    """
    global _mcp_client, _pm_mcp_config
    
    if _pm_mcp_config is None:
        raise RuntimeError(
            "PM MCP client not configured. "
            "Call configure_pm_mcp_client() first."
        )
    
    try:
        # Create MCP client if not already created
        if _mcp_client is None:
            logger.info("Creating PM MCP client...")
            _mcp_client = MultiServerMCPClient(_pm_mcp_config)
            logger.info("PM MCP client created successfully")
        
        # Get all tools from MCP server
        logger.info("Loading PM tools from MCP server...")
        all_tools = await _mcp_client.get_tools()
        
        # Filter tools if enabled_tools is specified
        enabled_tools = _pm_mcp_config["pm-server"].get("enabled_tools")
        if enabled_tools:
            filtered_tools = [
                tool for tool in all_tools
                if tool.name in enabled_tools
            ]
            logger.info(
                f"Loaded {len(filtered_tools)} PM tools from MCP server "
                f"(filtered from {len(all_tools)} total)"
            )
            return filtered_tools
        else:
            logger.info(f"Loaded {len(all_tools)} PM tools from MCP server")
            return all_tools
            
    except Exception as e:
        logger.error(f"Error loading PM tools from MCP server: {e}", exc_info=True)
        raise RuntimeError(f"Failed to load PM tools from MCP server: {e}")


def is_pm_mcp_configured() -> bool:
    """
    Check if PM MCP client is configured.
    
    Returns:
        True if configured, False otherwise
    """
    return _pm_mcp_config is not None


def get_pm_mcp_config() -> Optional[dict]:
    """
    Get the current PM MCP configuration.
    
    Returns:
        Configuration dictionary or None if not configured
    """
    return _pm_mcp_config


def reset_pm_mcp_client() -> None:
    """
    Reset the PM MCP client (useful for testing).
    """
    global _mcp_client, _pm_mcp_config
    _mcp_client = None
    _pm_mcp_config = None
    logger.info("PM MCP client reset")


# Convenience function for backward compatibility
async def get_pm_tools_via_mcp(
    server_url: str = "http://localhost:8080",
    transport: str = "sse",
    enabled_tools: Optional[list[str]] = None
) -> list:
    """
    Convenience function to configure and get PM tools in one call.
    
    Args:
        server_url: PM MCP Server URL
        transport: Transport type ("sse" or "stdio")
        enabled_tools: List of specific tools to enable
        
    Returns:
        List of PM tools from MCP server
        
    Example:
        # Quick setup for researcher agent
        pm_tools = await get_pm_tools_via_mcp(
            server_url="http://localhost:8080",
            enabled_tools=["list_projects", "list_my_tasks"]
        )
    """
    if not is_pm_mcp_configured():
        configure_pm_mcp_client(
            transport=transport,
            url=server_url,
            enabled_tools=enabled_tools
        )
    
    return await get_pm_mcp_tools()

