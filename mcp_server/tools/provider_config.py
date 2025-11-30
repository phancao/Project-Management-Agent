"""
PM Provider Configuration Tools

Allows users to configure PM providers (JIRA, OpenProject, etc.) directly via MCP tools.
This enables users to add their credentials without needing a web UI.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID
from mcp.types import TextContent
from sqlalchemy import func

logger = logging.getLogger(__name__)


def _register_tool(
    tool_func: Any,
    tool_names: list[str] | None = None,
    tool_functions: dict[str, Any] | None = None,
) -> None:
    """
    Helper function to register a tool function.
    
    Automatically extracts the tool name from the function name and registers it.
    This avoids hardcoding tool names and reduces errors.
    
    Args:
        tool_func: The tool function to register
        tool_names: Optional list to track tool names
        tool_functions: Optional dict to store tool functions for routing
    """
    tool_name = tool_func.__name__
    if tool_names is not None:
        tool_names.append(tool_name)
    if tool_functions is not None:
        tool_functions[tool_name] = tool_func


def register_provider_config_tools(
    server: Any,
    context: Any,  # ToolContext or pm_handler for backward compatibility
    config: Any = None,
    tool_names: list[str] | None = None,
    tool_functions: dict[str, Any] | None = None,
) -> int:
    """
    Register PM provider configuration tools.
    
    These tools allow users to configure their PM provider credentials
    directly from Cursor (or any MCP client) without needing a web UI.
    
    Args:
        server: MCP server instance
        context: ToolContext instance (or pm_handler for backward compatibility)
        config: Server configuration (optional)
        tool_names: Optional list to track tool names
        tool_functions: Optional dict to store tool functions
        
    Returns:
        Number of tools registered
    """
    tool_count = 0
    
    # Tool: list_providers
    @server.call_tool()
    async def list_providers(tool_name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """
        List all configured PM providers (both active and inactive).
        
        **CRITICAL**: Use this tool FIRST before attempting to list projects or tasks.
        If this returns no active providers, you MUST configure a provider using
        `configure_pm_provider` before you can retrieve any project data.
        
        **Workflow**:
        1. Call this tool first to check provider status
        2. If no active providers exist, use `configure_pm_provider` to set one up
        3. For demo/testing: Configure provider_type="mock" (no credentials needed)
        4. Then call `list_projects`, `list_tasks`, etc.
        
        Args:
            active_only (optional): If True, only return active providers (default: False)
        
        Returns:
            List of providers with:
            - id: Provider ID
            - name: Provider name
            - provider_type: Type (jira, openproject, clickup, mock)
            - is_active: Whether provider is active
            - base_url: Provider base URL
            - status: Configuration status message
        """
        try:
            from ..database.connection import get_mcp_db_session
            from ..database.models import PMProviderConnection
            
            active_only = arguments.get("active_only", False)
            
            # Get MCP Server database session
            db = next(get_mcp_db_session())
            try:
                query = db.query(PMProviderConnection)
                if active_only:
                    query = query.filter(PMProviderConnection.is_active == True)
                
                # Exclude mock providers - they are UI-only and not used in MCP Server
                query = query.filter(PMProviderConnection.provider_type != "mock")
                
                providers = query.all()
                
                if not providers:
                    return [TextContent(
                        type="text",
                        text="No PM providers configured. "
                             "Use the 'configure_pm_provider' tool to set up a provider. "
                             "Note: Mock providers are UI-only and not supported in MCP Server. "
                             "Please configure a real provider (jira, openproject, openproject_v13, clickup) with proper credentials."
                    )]
                
                # Format provider list
                output_lines = [f"Found {len(providers)} provider(s):\n"]
                for i, provider in enumerate(providers, 1):
                    status = "✅ Active" if provider.is_active else "❌ Inactive"
                    output_lines.append(
                        f"{i}. **{provider.name}** ({status})\n"
                        f"   ID: {provider.id}\n"
                        f"   Type: {provider.provider_type}\n"
                        f"   URL: {provider.base_url}\n"
                    )
                
                active_count = sum(1 for p in providers if p.is_active)
                output_lines.append(f"\nActive providers: {active_count}/{len(providers)}")
                
                if active_count == 0:
                    output_lines.append(
                        "\n⚠️ No active providers found. "
                        "Use 'configure_pm_provider' to set up a provider before listing projects."
                    )
                
                return [TextContent(
                    type="text",
                    text="\n".join(output_lines)
                )]
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error listing providers: {e}", exc_info=True)
            return [TextContent(
                type="text",
                text=f"Error listing providers: {str(e)}"
            )]
    
    # Register tool automatically using helper function
    _register_tool(list_providers, tool_names, tool_functions)
    tool_count += 1
    
    # Tool: configure_pm_provider
    @server.call_tool()
    async def configure_pm_provider(tool_name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """
        Configure a PM provider (JIRA, OpenProject, ClickUp) for the current user.
        
        **IMPORTANT**: Mock providers are UI-only and NOT supported in MCP Server.
        Do NOT configure mock providers using this tool. Mock providers are only
        available in the web UI for demonstration purposes.
        
        **WHEN TO USE THIS TOOL**:
        - After calling `list_providers` and finding no active providers
        - When user asks to "list my projects" but no providers are configured
        - When you need to set up a provider before retrieving project data
        
        **WORKFLOW**:
        1. Call `list_providers` first to check current provider status
        2. If no active providers exist, use this tool to configure one
        3. For real providers: User must provide credentials (api_key, api_token, etc.)
        4. After configuration, call `list_projects` to retrieve projects
        
        Args:
            provider_type (required): Type of provider - "jira", "openproject", "openproject_v13", "clickup"
            NOTE: "mock" is NOT supported - mock providers are UI-only
            base_url (required): Base URL of the provider (e.g., "https://company.atlassian.net")
            api_token (optional): API token for JIRA
            api_key (optional): API key for OpenProject or ClickUp
            username (optional): Username/email - required for JIRA (use your email address)
            organization_id (optional): Organization/Team ID for ClickUp
            workspace_id (optional): Workspace ID for OpenProject
            name (optional): Custom name for this provider connection
        
        Returns:
            Success message with provider ID and number of projects found, or error message
        
        Example for JIRA:
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
            
            # Fallback: try to get from context if it has user_id
            if not user_id and hasattr(context, 'user_id'):
                user_id = context.user_id
                logger.info(f"[configure_pm_provider] Got user_id from context: {user_id}")
            
            # User ID is required for all provider configurations
            if not user_id:
                logger.warning("[configure_pm_provider] No user_id found in context")
                return [TextContent(
                    type="text",
                    text="Error: User ID not found in MCP connection context. "
                         "Please ensure you're connected with a valid MCP API key. "
                         "The configure_pm_provider tool requires user authentication. "
                         "Make sure you're connecting with X-MCP-API-Key header or X-User-ID header."
                )]
            
            # Validate required fields
            provider_type = arguments.get("provider_type")
            base_url = arguments.get("base_url")
            
            if not provider_type:
                return [TextContent(
                    type="text",
                    text="Error: provider_type is required (jira, openproject, openproject_v13, clickup). "
                         "Note: mock providers are UI-only and not supported in MCP Server."
                )]
            
            # Reject mock provider configuration - mock providers are UI-only
            if provider_type == "mock":
                return [TextContent(
                    type="text",
                    text="Error: Mock providers are UI-only and cannot be configured in MCP Server. "
                         "Mock providers are only available in the web UI for demonstration purposes. "
                         "Please use a real provider type (jira, openproject, openproject_v13, clickup) "
                         "with proper credentials."
                )]
            
            # All real providers require base_url
            if not base_url:
                return [TextContent(
                    type="text",
                    text="Error: base_url is required for all provider types"
                )]
            
            # Normalize base_url to prevent duplicates (remove trailing slash)
            # This ensures 'http://example.com' and 'http://example.com/' are treated as the same
            if base_url:
                base_url = base_url.rstrip('/')
            
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
                # Ensure the user exists in database
                from ..database.models import User
                from uuid import UUID
                user_id_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
                user = db.query(User).filter(User.id == user_id_uuid).first()
                if not user:
                    # User should exist if authenticated, but create if missing
                    user = User(
                        id=user_id_uuid,
                        email=f"user_{user_id_uuid}@mcp",
                        name="MCP User",
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    db.add(user)
                    db.commit()
                    logger.info(f"[configure_pm_provider] Created user: {user_id}")
                
                # Check if provider already exists for this user
                # Normalize stored base_url for comparison (remove trailing slash)
                # This prevents duplicates from URL format differences
                existing = db.query(PMProviderConnection).filter(
                    PMProviderConnection.created_by == user_id_uuid,
                    PMProviderConnection.provider_type == provider_type,
                    # Use func.rtrim to normalize base_url in database for comparison
                    func.rtrim(PMProviderConnection.base_url, '/') == base_url,
                    PMProviderConnection.is_active == True
                ).first()
                
                provider_name = arguments.get("name") or f"{provider_type} - {base_url}"
                
                if existing:
                    # Update existing provider instead of rejecting
                    logger.info(f"[configure_pm_provider] Updating existing provider: {existing.id}")
                    existing.name = provider_name
                    # Update credentials if provided (use new values, fallback to existing if None)
                    if "api_key" in arguments:
                        existing.api_key = arguments.get("api_key")
                    if "api_token" in arguments:
                        existing.api_token = arguments.get("api_token")
                    if "username" in arguments:
                        existing.username = arguments.get("username")
                    if "organization_id" in arguments:
                        existing.organization_id = arguments.get("organization_id")
                    if "workspace_id" in arguments:
                        existing.workspace_id = arguments.get("workspace_id")
                    existing.updated_at = datetime.utcnow()
                    provider = existing
                    db.commit()
                    db.refresh(provider)
                    logger.info(f"[configure_pm_provider] Updated provider: {provider.id}")
                else:
                    # Create new provider connection
                    provider = PMProviderConnection(
                        name=provider_name,
                        provider_type=provider_type,
                        base_url=base_url,
                        api_key=arguments.get("api_key"),
                        api_token=arguments.get("api_token"),
                        username=arguments.get("username"),
                        organization_id=arguments.get("organization_id"),
                        workspace_id=arguments.get("workspace_id"),
                        created_by=user_id_uuid,  # ✅ User-scoped (UUID format)
                        is_active=True
                    )
                    
                    db.add(provider)
                    db.commit()
                    db.refresh(provider)
                    logger.info(f"[configure_pm_provider] Created new provider: {provider.id}")
                
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
    
    # Register tool automatically using helper function
    _register_tool(configure_pm_provider, tool_names, tool_functions)
    tool_count += 1
    
    logger.info(f"Registered {tool_count} provider configuration tool(s)")
    return tool_count

