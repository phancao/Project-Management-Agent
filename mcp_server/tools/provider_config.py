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
    tool_functions: dict[str, Any] | None = None,
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
                
                providers = query.all()
                
                if not providers:
                    return [TextContent(
                        type="text",
                        text="No PM providers configured. "
                             "Use the 'configure_pm_provider' tool to set up a provider. "
                             "For demo/testing, use provider_type='mock' (no credentials needed)."
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
    
    # Track tool name and store function reference after function is defined
    if tool_names is not None:
        tool_names.append("list_providers")
    if tool_functions is not None:
        tool_functions["list_providers"] = list_providers
    tool_count += 1
    
    # Tool: configure_pm_provider
    @server.call_tool()
    async def configure_pm_provider(tool_name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """
        Configure a PM provider (JIRA, OpenProject, ClickUp, Mock) for the current user.
        
        **WHEN TO USE THIS TOOL**:
        - After calling `list_providers` and finding no active providers
        - When user asks to "list my projects" but no providers are configured
        - When you need to set up a provider before retrieving project data
        
        **WORKFLOW**:
        1. Call `list_providers` first to check current provider status
        2. If no active providers exist, use this tool to configure one
        3. For demo/testing: Use provider_type="mock" (no credentials needed, has demo data)
        4. For real providers: User must provide credentials (api_key, api_token, etc.)
        5. After configuration, call `list_projects` to retrieve projects
        
        **Mock Provider (Recommended for Testing)**:
        - No credentials required
        - Contains demo projects, tasks, sprints, epics
        - Perfect for testing and demonstrations
        - Example: configure_pm_provider({"provider_type": "mock", "base_url": "http://localhost", "name": "Demo Provider"})
        
        Args:
            provider_type (required): Type of provider - "jira", "openproject", "clickup", "mock"
            base_url (required): Base URL of the provider (e.g., "https://company.atlassian.net")
            api_token (optional): API token for JIRA
            api_key (optional): API key for OpenProject or ClickUp
            username (optional): Username/email - required for JIRA (use your email address)
            organization_id (optional): Organization/Team ID for ClickUp
            workspace_id (optional): Workspace ID for OpenProject
            name (optional): Custom name for this provider connection
        
        Returns:
            Success message with provider ID and number of projects found, or error message
        
        Example for Mock provider (demo data, no credentials):
            configure_pm_provider({
                "provider_type": "mock",
                "base_url": "http://localhost",
                "name": "Mock Provider (Demo Data)"
            })
        
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
                    text="Error: provider_type is required (jira, openproject, clickup, mock)"
                )]
            
            # Mock provider doesn't need base_url or credentials
            if provider_type != "mock" and not base_url:
                return [TextContent(
                    type="text",
                    text="Error: base_url is required (except for mock provider)"
                )]
            
            # Mock provider: no validation needed, just create it
            if provider_type == "mock":
                # Mock provider doesn't need base_url, but we'll use a default
                if not base_url:
                    base_url = "http://localhost"
            
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
                    # Handle mock provider separately (not in factory)
                    if provider_type == "mock":
                        from pm_providers.mock_provider import MockPMProvider
                        from pm_providers.models import PMProviderConfig
                        # Mock provider needs base_url as string
                        mock_base_url = base_url or "http://localhost"
                        config = PMProviderConfig(
                            provider_type="mock",
                            base_url=mock_base_url,
                        )
                        provider_instance = MockPMProvider(config)
                    else:
                        provider_instance = create_pm_provider(
                            provider_type=provider_type,
                            base_url=base_url,
                            api_key=arguments.get("api_key"),
                            api_token=arguments.get("api_token"),
                            username=arguments.get("username"),
                            organization_id=arguments.get("organization_id"),
                            workspace_id=arguments.get("workspace_id"),
                        )
                    
                    # Test health check (mock provider always returns True)
                    if provider_type != "mock":
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
    
    # Track tool name and store function reference after function is defined
    if tool_names is not None:
        tool_names.append("configure_pm_provider")
    if tool_functions is not None:
        tool_functions["configure_pm_provider"] = configure_pm_provider
    tool_count += 1
    
    logger.info(f"Registered {tool_count} provider configuration tool(s)")
    return tool_count

