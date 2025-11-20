"""
PM Provider Configuration Tools

Allows users to configure PM providers (JIRA, OpenProject, etc.) directly via MCP tools.
This enables users to add their credentials without needing a web UI.
"""

import logging
from typing import Any
from mcp.types import TextContent

logger = logging.getLogger(__name__)


def register_provider_config_tools(
    server: Any,
    pm_handler: Any,
    config: Any,
    tool_names: list[str] | None = None,
) -> int:
    """
    Register PM provider configuration tools.
    
    These tools allow users to configure their PM provider credentials
    directly from Cursor (or any MCP client) without needing a web UI.
    
    Args:
        server: MCP server instance
        pm_handler: PM handler instance (not used, but kept for consistency)
        config: Server configuration
        tool_names: Optional list to track tool names
        
    Returns:
        Number of tools registered
    """
    tool_count = 0
    
    # Tool: configure_pm_provider
    @server.call_tool()
    async def configure_pm_provider(arguments: dict[str, Any]) -> list[TextContent]:
        """
        Configure a PM provider (JIRA, OpenProject, ClickUp) for the current user.
        
        This tool allows users to add their PM provider credentials directly
        from Cursor without needing a web UI.
        
        Args:
            provider_type (required): Type of provider - "jira", "openproject", "clickup"
            base_url (required): Base URL of the provider (e.g., "https://company.atlassian.net")
            api_token (optional): API token for JIRA
            api_key (optional): API key for OpenProject or ClickUp
            username (optional): Username/email - required for JIRA (use your email address)
            organization_id (optional): Organization/Team ID for ClickUp
            workspace_id (optional): Workspace ID for OpenProject
            name (optional): Custom name for this provider connection
        
        Returns:
            Success message with provider ID
        
        Example:
            configure_pm_provider({
                "provider_type": "jira",
                "base_url": "https://company.atlassian.net",
                "api_token": "ATATT3xFfGF0abc123...",
                "username": "user@company.com",
                "name": "My JIRA"
            })
        """
        try:
            from ..database.connection import get_mcp_db_session
            from ..database.models import PMProviderConnection
            from pm_providers.factory import create_pm_provider
            
            # Get user_id from MCP server context
            # The MCP server instance should have user_id set when connection is established
            user_id = None
            
            # Try to get user_id from the server's parent PMMCPServer instance
            # The server object should have access to the PMMCPServer instance
            if hasattr(server, '_mcp_server_instance'):
                mcp_server = server._mcp_server_instance
                user_id = getattr(mcp_server, 'user_id', None)
                logger.info(f"[configure_pm_provider] Got user_id from server instance: {user_id}")
            
            # Fallback: try to get from pm_handler if it has user_id
            if not user_id and hasattr(pm_handler, 'user_id'):
                user_id = pm_handler.user_id
                logger.info(f"[configure_pm_provider] Got user_id from pm_handler: {user_id}")
            
            if not user_id:
                logger.warning("[configure_pm_provider] No user_id found in context")
                return [TextContent(
                    type="text",
                    text="Error: User ID not found in MCP connection context. "
                         "Please ensure you're connected with a valid MCP API key. "
                         "The configure_pm_provider tool requires user authentication. "
                         "Make sure you're connecting with X-MCP-API-Key header."
                )]
            
            # Validate required fields
            provider_type = arguments.get("provider_type")
            base_url = arguments.get("base_url")
            
            if not provider_type:
                return [TextContent(
                    type="text",
                    text="Error: provider_type is required (jira, openproject, clickup)"
                )]
            
            if not base_url:
                return [TextContent(
                    type="text",
                    text="Error: base_url is required"
                )]
            
            # Provider-specific validation
            if provider_type == "jira":
                api_token = arguments.get("api_token")
                username = arguments.get("username")
                
                if not api_token:
                    return [TextContent(
                        type="text",
                        text="Error: api_token is required for JIRA"
                    )]
                
                if not username:
                    return [TextContent(
                        type="text",
                        text="Error: username (email) is required for JIRA"
                    )]
            
            elif provider_type in ["openproject", "openproject_v13"]:
                api_key = arguments.get("api_key")
                if not api_key:
                    return [TextContent(
                        type="text",
                        text="Error: api_key is required for OpenProject"
                    )]
            
            elif provider_type == "clickup":
                api_key = arguments.get("api_key")
                if not api_key:
                    return [TextContent(
                        type="text",
                        text="Error: api_key is required for ClickUp"
                    )]
            
            # Get MCP Server database session (independent from backend)
            db = next(get_mcp_db_session())
            try:
                # Check if provider already exists for this user
                existing = db.query(PMProviderConnection).filter(
                    PMProviderConnection.created_by == user_id,
                    PMProviderConnection.provider_type == provider_type,
                    PMProviderConnection.base_url == base_url,
                    PMProviderConnection.is_active == True
                ).first()
                
                if existing:
                    return [TextContent(
                        type="text",
                        text=f"Provider already configured: {existing.id}. "
                             f"Use update_pm_provider to modify it."
                    )]
                
                # Create provider connection
                provider_name = arguments.get("name") or f"{provider_type} - {base_url}"
                provider = PMProviderConnection(
                    name=provider_name,
                    provider_type=provider_type,
                    base_url=base_url,
                    api_key=arguments.get("api_key"),
                    api_token=arguments.get("api_token"),
                    username=arguments.get("username"),
                    organization_id=arguments.get("organization_id"),
                    workspace_id=arguments.get("workspace_id"),
                    created_by=user_id,  # ✅ User-scoped
                    is_active=True
                )
                
                db.add(provider)
                db.commit()
                db.refresh(provider)
                
                # Test connection
                try:
                    provider_instance = create_pm_provider(
                        provider_type=provider_type,
                        base_url=base_url,
                        api_key=arguments.get("api_key"),
                        api_token=arguments.get("api_token"),
                        username=arguments.get("username"),
                        organization_id=arguments.get("organization_id"),
                        workspace_id=arguments.get("workspace_id"),
                    )
                    
                    # Test health check
                    is_healthy = await provider_instance.health_check()
                    if not is_healthy:
                        return [TextContent(
                            type="text",
                            text=f"Warning: Provider configured (ID: {provider.id}) but health check failed. "
                                 f"Please verify your credentials."
                        )]
                    
                    # Try to list projects to verify
                    projects = await provider_instance.list_projects()
                    
                    return [TextContent(
                        type="text",
                        text=f"✅ Provider configured successfully!\n"
                             f"Provider ID: {provider.id}\n"
                             f"Name: {provider_name}\n"
                             f"Type: {provider_type}\n"
                             f"Found {len(projects)} project(s).\n"
                             f"You can now use list_projects, create_task, and other PM tools."
                    )]
                    
                except Exception as test_error:
                    # Provider saved but connection test failed
                    error_msg = str(test_error)
                    return [TextContent(
                        type="text",
                        text=f"⚠️ Provider saved (ID: {provider.id}) but connection test failed:\n"
                             f"{error_msg}\n"
                             f"Please verify your credentials are correct."
                    )]
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error configuring provider: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error configuring provider: {str(e)}"
            )]
    
    if tool_names is not None:
        tool_names.append("configure_pm_provider")
    tool_count += 1
    
    logger.info(f"Registered {tool_count} provider configuration tool(s)")
    return tool_count

