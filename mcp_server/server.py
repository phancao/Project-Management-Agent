"""
PM MCP Server Implementation

Main server class that registers PM tools and handles MCP protocol communication.
"""

import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import ToolsCapability
from sqlalchemy.orm import Session

from .database.connection import get_mcp_db_session, init_mcp_db
from .pm_handler import MCPPMHandler
from .config import PMServerConfig
from .core.tool_context import ToolContext
from .tools import (
    register_project_tools,
    register_task_tools,
    register_sprint_tools,
    register_epic_tools,
    register_user_tools,
    register_analytics_tools,
    register_task_interaction_tools,
)
from .tools.provider_config import register_provider_config_tools
from .tools.analytics_v2.register import register_analytics_tools_v2
from .tools.projects_v2.register import register_project_tools_v2
from .tools.tasks_v2.register import register_task_tools_v2
from .tools.sprints_v2.register import register_sprint_tools_v2
from .tools.epics_v2.register import register_epic_tools_v2

logger = logging.getLogger(__name__)


class PMMCPServer:
    """
    PM MCP Server
    
    Exposes Project Management operations as MCP tools for AI agents.
    Supports multiple PM providers (OpenProject, JIRA, ClickUp, Internal DB).
    """
    
    def __init__(self, config: PMServerConfig | None = None, user_id: str | None = None):
        """
        Initialize PM MCP Server.
        
        Args:
            config: Server configuration. If None, loads from environment.
            user_id: Optional user ID for user-scoped credential loading.
                     If provided, only loads providers where created_by = user_id.
        """
        self.config = config or PMServerConfig.from_env()
        self.config.validate()
        
        # User context for credential scoping
        self.user_id = user_id
        
        # Initialize MCP server
        self.server = Server(self.config.server_name)
        
        # Database session
        self.db_session: Session | None = None
        
        # PM Handler (will be initialized when server starts)
        self.pm_handler: MCPPMHandler | None = None
        
        # Tool Context (NEW: provides unified context for refactored tools)
        self.tool_context: ToolContext | None = None
        
        # Tool registry
        self.registered_tools: list[str] = []
        
        # Track registered tool names for list_tools
        # This list will be populated as tools are registered
        self._tool_names: list[str] = []
        # Store tool function references for direct access (bypassing CallToolRequest routing bug)
        self._tool_functions: dict[str, Any] = {}
        
        logger.info(
            f"PM MCP Server initialized: {self.config.server_name} v{self.config.server_version}"
        )
    
    def _initialize_pm_handler(self) -> None:
        """Initialize PM Handler with database session and user context."""
        if self.pm_handler is not None:
            return
        
        logger.info("Initializing PM Handler...")
        
        # Get MCP Server database session (independent from backend)
        self.db_session = next(get_mcp_db_session())
        
        # Initialize PMHandler with user context if provided
        if self.user_id:
            logger.info(f"Initializing PM Handler for user: {self.user_id}")
            self.pm_handler = MCPPMHandler.from_db_session_and_user(
                self.db_session, 
                user_id=self.user_id
            )
        else:
            logger.info("Initializing PM Handler for all users (backward compatible)")
            self.pm_handler = MCPPMHandler.from_db_session(self.db_session)
        
        # Get provider count
        provider_count = len(self.pm_handler._get_active_providers())
        
        logger.info(
            f"PM Handler initialized with {provider_count} active provider(s)"
            + (f" for user {self.user_id}" if self.user_id else " (all users)")
        )
        
        # Initialize Tool Context (NEW: for refactored tools)
        logger.info("Initializing Tool Context...")
        self.tool_context = ToolContext(
            db_session=self.db_session,
            user_id=self.user_id
        )
        logger.info("Tool Context initialized")
    
    def _register_all_tools(self) -> None:
        """Register all PM tools with the MCP server."""
        if self.pm_handler is None:
            raise RuntimeError("PM Handler not initialized. Call _initialize_pm_handler first.")
        
        logger.info("Registering PM tools...")
        
        # Register tools from each module
        tool_modules = [
            ("provider_config", register_provider_config_tools),  # Provider config tools
            ("users", register_user_tools),  # User tools
            ("task_interactions", register_task_interaction_tools),  # Task interactions
            # V2 Tools (NEW: Refactored with new architecture)
            ("analytics_v2", register_analytics_tools_v2),  # Analytics tools (refactored)
            ("projects_v2", register_project_tools_v2),  # Project tools (hybrid)
            ("tasks_v2", register_task_tools_v2),  # Task tools (hybrid)
            ("sprints_v2", register_sprint_tools_v2),  # Sprint tools (hybrid)
            ("epics_v2", register_epic_tools_v2),  # Epic tools (hybrid)
        ]
        
        for module_name, register_func in tool_modules:
            try:
                # Pass tool_names list and tool_functions dict to registration functions
                # so they can track tool names and store function references
                import inspect
                sig = inspect.signature(register_func)
                param_names = list(sig.parameters.keys())
                
                # NEW: Check if function expects tool_context (for refactored tools)
                if "context" in param_names:
                    # Refactored tools signature: (server, context, tool_names, tool_functions)
                    logger.info(f"[{module_name}] Using refactored tools signature (with context)")
                    count = register_func(self.server, self.tool_context, self._tool_names, self._tool_functions)
                elif len(sig.parameters) >= 5:
                    # New signature: (server, pm_handler, config, tool_names, tool_functions)
                    count = register_func(self.server, self.pm_handler, self.config, self._tool_names, self._tool_functions)
                elif len(sig.parameters) >= 4:
                    # Old signature: (server, pm_handler, config, tool_names)
                    count = register_func(self.server, self.pm_handler, self.config, self._tool_names)
                else:
                    # Very old signature: (server, pm_handler, config)
                    count = register_func(self.server, self.pm_handler, self.config)
                self.registered_tools.extend([f"{module_name}.*"])
                logger.info(f"Registered {count} {module_name} tools")
            except Exception as e:
                logger.error(f"Failed to register {module_name} tools: {e}")
                raise
        
        logger.info(f"Total tools registered: {len(self.registered_tools)}")
        
        # CRITICAL: Create a single routing handler for all tool calls
        # The SDK's call_tool() decorator overwrites the handler each time, so we need
        # a single handler that routes to the correct tool function based on tool_name
        logger.info("Creating single routing handler for all tool calls...")
        from mcp.types import CallToolRequest, CallToolResult, TextContent
        
        # Store reference to tool_functions for the routing handler
        tool_functions = self._tool_functions
        
        @self.server.call_tool()
        async def route_tool_call(tool_name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """
            Single routing handler for all tool calls.
            Routes to the correct tool function based on tool_name.
            """
            logger.info(f"[ROUTER] Routing tool call: {tool_name}")
            
            # Get the tool function from our stored functions
            if tool_name not in tool_functions:
                logger.error(f"[ROUTER] Tool '{tool_name}' not found in tool_functions")
                logger.error(f"[ROUTER] Available tools: {list(tool_functions.keys())[:10]}")
                return [TextContent(
                    type="text",
                    text=f"Error: Tool '{tool_name}' not found. Available tools: {', '.join(list(tool_functions.keys())[:10])}"
                )]
            
            tool_func = tool_functions[tool_name]
            logger.info(f"[ROUTER] Found tool function for '{tool_name}': {tool_func}")
            
            try:
                # Call the tool function with (tool_name, arguments)
                result = await tool_func(tool_name, arguments)
                logger.info(f"[ROUTER] Tool '{tool_name}' completed successfully")
                return result
            except Exception as e:
                logger.error(f"[ROUTER] Error calling tool '{tool_name}': {e}", exc_info=True)
                return [TextContent(
                    type="text",
                    text=f"Error calling tool '{tool_name}': {str(e)}"
                )]
        
        logger.info(f"✅ Routing handler created. {len(tool_functions)} tools available for routing.")
        
        # CRITICAL: Register list_tools handler so the SDK automatically enables tools capability
        # The MCP SDK (v1.21.2) automatically enables tools capability when @server.list_tools() is registered
        # The handler below will be detected by the SDK and tools capability will be enabled automatically
        from mcp.types import Tool
        
        logger.info("Registering list_tools handler...")
        try:
            @self.server.list_tools()
            async def list_all_tools(request=None) -> list[Tool]:
                """
                List all registered PM tools.
                
                This handler is required for the MCP SDK to automatically enable
                the tools capability in initialization options.
                
                The SDK supports both return types:
                - list[Tool] (old style) - SDK wraps it in ListToolsResult
                - ListToolsResult (new style) - SDK uses it directly
                """
                logger.info("=" * 80)
                logger.info("[list_all_tools] Handler called!")
                logger.info(f"[list_all_tools] Tracked tool names: {len(self._tool_names)}")
                if self._tool_names:
                    logger.info(f"[list_all_tools] Tool names (first 10): {self._tool_names[:10]}")
                logger.info(f"[list_all_tools] Cache size: {len(self.server._tool_cache)}")
                if hasattr(self.server, '_tool_cache') and self.server._tool_cache:
                    logger.info(f"[list_all_tools] Cache keys (first 5): {list(self.server._tool_cache.keys())[:5]}")
                
                try:
                    # First try to get tools from cache (if SDK populated it)
                    tools = list(self.server._tool_cache.values())
                    logger.info(f"[list_all_tools] Found {len(tools)} tools in cache")
                    
                    # If cache is empty, manually build Tool objects from tracked tool names
                    # The SDK's _get_cached_tool_definition doesn't work because tools aren't in cache
                    # So we'll build basic Tool objects that allow the tools to be called
                    if not tools and self._tool_names:
                        logger.info(f"[list_all_tools] Cache empty, manually building {len(self._tool_names)} Tool objects...")
                        built_tools = []
                        
                        # Try _get_cached_tool_definition first (in case SDK can build them)
                        for tool_name in self._tool_names:
                            try:
                                tool_def = await self.server._get_cached_tool_definition(tool_name)
                                if tool_def:
                                    built_tools.append(tool_def)
                                    logger.debug(f"[list_all_tools] Got tool definition from SDK: {tool_name}")
                                    continue
                            except Exception as e:
                                logger.debug(f"[list_all_tools] SDK couldn't build {tool_name}: {e}")
                        
                        # For tools that SDK couldn't build, create basic Tool objects
                        # These will allow tools to be called even without full schema
                        remaining_names = [name for name in self._tool_names if name not in [t.name for t in built_tools]]
                        if remaining_names:
                            logger.info(f"[list_all_tools] Manually creating {len(remaining_names)} Tool objects...")
                            for tool_name in remaining_names:
                                # Create a basic Tool object with generic schema
                                # The actual tool function will handle validation
                                tool = Tool(
                                    name=tool_name,
                                    description=f"Tool: {tool_name}",
                                    inputSchema={
                                        "type": "object",
                                        "properties": {},
                                        "additionalProperties": True
                                    }
                                )
                                built_tools.append(tool)
                                logger.debug(f"[list_all_tools] Created basic Tool object: {tool_name}")
                        
                        tools = built_tools
                        logger.info(f"[list_all_tools] Built {len(tools)} tools total ({len(built_tools) - len(remaining_names)} from SDK, {len(remaining_names)} manual)")
                    
                    # If still no tools, return empty list (but log warning)
                    if not tools:
                        logger.warning(f"[list_all_tools] Returning 0 tools (cache empty, {len(self._tool_names)} tool names tracked)")
                    else:
                        logger.info(f"[list_all_tools] Returning {len(tools)} tools")
                        logger.debug(f"[list_all_tools] Tool names: {[t.name for t in tools[:5]]}...")  # First 5
                    
                    logger.info("=" * 80)
                    
                    # Return ListToolsResult explicitly (SDK v1.21.2 expects this)
                    from mcp.types import ListToolsResult
                    return ListToolsResult(tools=tools)
                except Exception as e:
                    logger.error(f"[list_all_tools] ERROR: {e}", exc_info=True)
                    logger.error("=" * 80)
                    # Return empty ListToolsResult on error
                    from mcp.types import ListToolsResult
                    return ListToolsResult(tools=[])
            
            # Verify handler is actually registered
            from mcp.types import ListToolsRequest
            if ListToolsRequest in self.server.request_handlers:
                handler = self.server.request_handlers[ListToolsRequest]
                logger.info(f"✅ list_tools handler registered successfully")
                logger.info(f"   Handler type: {type(handler)}")
                logger.info(f"   Handler: {handler}")
            else:
                logger.error("❌ list_tools handler NOT found in request_handlers!")
                logger.error(f"   Available handlers: {list(self.server.request_handlers.keys())}")
                raise RuntimeError("list_tools handler not registered")
        except Exception as e:
            logger.error(f"❌ Failed to register list_tools handler: {e}", exc_info=True)
            raise
    
    async def run_stdio(self) -> None:
        """
        Run server with stdio transport.
        
        This is the standard transport for Claude Desktop and similar clients.
        """
        logger.info("Starting PM MCP Server with stdio transport...")
        
        try:
            # Initialize PM Handler
            self._initialize_pm_handler()
            
            # Register all tools
            self._register_all_tools()
            
            # Run server with stdio
            async with stdio_server() as (read_stream, write_stream):
                logger.info("PM MCP Server running on stdio")
                
                # Enable debug logging for MCP server
                mcp_logger = logging.getLogger("mcp")
                mcp_logger.setLevel(logging.DEBUG)
                mcp_server_logger = logging.getLogger("mcp.server")
                mcp_server_logger.setLevel(logging.DEBUG)
                
                # Log registered tools count if available
                tools_count = 0
                try:
                    # Check multiple possible attributes where tools might be stored
                    tools_dict = None
                    
                    # Try _tools first (older MCP SDK versions)
                    if hasattr(self.server, '_tools'):
                        tools_dict = getattr(self.server, '_tools', {})
                        logger.info("Found tools in _tools attribute")
                    
                    # Try _tool_cache (newer MCP SDK versions)
                    if hasattr(self.server, '_tool_cache'):
                        tool_cache = getattr(self.server, '_tool_cache', {})
                        logger.info(f"Found _tool_cache attribute: type={type(tool_cache)}")
                        
                        # _tool_cache might be a dict or a cache object
                        if isinstance(tool_cache, dict):
                            tools_dict = tool_cache
                            logger.info(f"_tool_cache is a dict with {len(tool_cache)} items")
                            if tool_cache:
                                logger.info(f"Sample keys: {list(tool_cache.keys())[:5]}")
                        else:
                            # It might be a cache object with a different structure
                            logger.info(f"_tool_cache is {type(tool_cache).__name__}, checking for tools inside...")
                            # Try to get tools from cache object
                            if hasattr(tool_cache, 'get'):
                                try:
                                    # Try to get all items
                                    all_items = tool_cache.get('*', {}) if callable(getattr(tool_cache, 'get', None)) else {}
                                    if all_items:
                                        tools_dict = all_items
                                        logger.info(f"Found tools in cache.get('*'): {len(all_items)} items")
                                except:
                                    pass
                            
                            # Check if it has a dict-like interface
                            if not tools_dict and hasattr(tool_cache, '__dict__'):
                                cache_dict = tool_cache.__dict__
                                logger.info(f"Cache __dict__ keys: {list(cache_dict.keys())[:5]}")
                                # Look for any dict-like structure
                                for key, value in cache_dict.items():
                                    if isinstance(value, dict) and len(value) > 0:
                                        tools_dict = value
                                        logger.info(f"Found tools dict in cache.{key}: {len(value)} items")
                                        break
                    
                    # Try _call_tool_handlers (alternative storage)
                    elif hasattr(self.server, '_call_tool_handlers'):
                        handlers = getattr(self.server, '_call_tool_handlers', {})
                        if isinstance(handlers, dict):
                            tools_dict = handlers
                            logger.info("Found tools in _call_tool_handlers attribute")
                    
                    # If we found tools, count them
                    if tools_dict:
                        tools_count = len(tools_dict) if isinstance(tools_dict, dict) else 0
                        logger.info(f"Server has {tools_count} tools registered")
                        if tools_count > 0:
                            # Log first few tool names for verification
                            tool_names = list(tools_dict.keys())[:5]
                            logger.info(f"Sample tool names: {tool_names}")
                    else:
                        logger.warning("Could not find tools in any known attribute")
                        # Log all attributes containing 'tool' for debugging
                        if hasattr(self.server, '__dict__'):
                            tool_attrs = [k for k in self.server.__dict__.keys() if 'tool' in k.lower()]
                            logger.info(f"Server attributes with 'tool': {tool_attrs}")
                        
                        # Try to call list_tools to see if it works
                        if hasattr(self.server, 'list_tools'):
                            try:
                                # Note: This might not work in this context, but worth trying
                                logger.info("Attempting to verify tools via list_tools method...")
                            except Exception as e:
                                logger.debug(f"Could not call list_tools here: {e}")
                except Exception as e:
                    logger.warning(f"Could not check tools count: {e}", exc_info=True)
                
                # Verify tools capability is enabled (SDK v1.21.2 should do this automatically when @server.list_tools() is registered)
                # This is just a verification/fallback - the SDK handles capability enabling automatically
                init_options = self.server.create_initialization_options()
                logger.debug(f"Initial initialization options: {init_options}")
                
                if init_options.capabilities and init_options.capabilities.tools:
                    if tools_count > 0:
                        logger.info(f"✅ Tools capability auto-enabled by SDK (with {tools_count} tools in cache)")
                    else:
                        logger.info("✅ Tools capability auto-enabled by SDK (tools will be built on-demand via list_tools handler)")
                else:
                    # Fallback: Manually enable if SDK didn't (shouldn't happen with @server.list_tools() registered in SDK v1.21.2)
                    logger.warning("⚠️  Tools capability not auto-enabled by SDK, enabling manually as fallback...")
                    from mcp.types import ServerCapabilities
                    
                    # Create new capabilities with tools enabled, preserving other capabilities
                    existing_caps = init_options.capabilities.__dict__ if init_options.capabilities else {}
                    new_capabilities = ServerCapabilities(
                        tools=ToolsCapability(list_changed=False),
                        experimental=existing_caps.get('experimental', {}),
                        logging=existing_caps.get('logging'),
                        prompts=existing_caps.get('prompts'),
                        resources=existing_caps.get('resources'),
                        completions=existing_caps.get('completions'),
                    )
                    init_options.capabilities = new_capabilities
                    logger.info("✅ Tools capability manually enabled (fallback)")
                
                logger.debug(f"Final initialization options: {init_options}")
                
                try:
                    # Verify handler is registered before starting server
                    from mcp.types import ListToolsRequest
                    if ListToolsRequest not in self.server.request_handlers:
                        logger.error("❌ CRITICAL: list_tools handler NOT registered before server.run()!")
                        logger.error(f"   Available handlers: {list(self.server.request_handlers.keys())}")
                        raise RuntimeError("list_tools handler not registered")
                    else:
                        logger.info(f"✅ Verified: list_tools handler is registered before server.run()")
                        handler = self.server.request_handlers[ListToolsRequest]
                        logger.info(f"   Handler: {handler}")
                    
                    logger.info("Starting server.run() - this should run indefinitely...")
                    
                    # Verify tools are actually registered by trying to list them
                    # This helps debug if tools are properly registered
                    try:
                        # Check if server has a method to list tools internally
                        if hasattr(self.server, '_list_tools_handler'):
                            logger.info("Server has _list_tools_handler")
                        if hasattr(self.server, 'list_tools'):
                            logger.info("Server has list_tools method")
                        
                        # Try to inspect registered call_tool handlers
                        if hasattr(self.server, '__dict__'):
                            all_attrs = [k for k in self.server.__dict__.keys()]
                            tool_related = [k for k in all_attrs if 'tool' in k.lower() or 'call' in k.lower()]
                            logger.info(f"Server attributes related to tools/calls: {tool_related}")
                            
                            # Try to find where call_tool decorator stores handlers
                            for attr in tool_related:
                                try:
                                    value = getattr(self.server, attr)
                                    if hasattr(value, '__len__'):
                                        length = len(value)
                                        logger.info(f"  {attr}: {type(value).__name__} with length {length}")
                                        if length > 0 and hasattr(value, 'keys'):
                                            logger.info(f"    Keys: {list(value.keys())[:5]}")
                                except:
                                    pass
                    except Exception as e:
                        logger.debug(f"Could not inspect server internals: {e}")
                    
                    # Add handler to catch and log any errors during request processing
                    import asyncio
                    async def run_with_error_handling():
                        try:
                            await self.server.run(
                                read_stream,
                                write_stream,
                                init_options
                            )
                        except asyncio.CancelledError:
                            logger.info("Server run cancelled (connection closed by client)")
                            raise
                        except Exception as e:
                            logger.error(f"Error during server.run(): {e}", exc_info=True)
                            raise
                    
                    await run_with_error_handling()
                    logger.warning("server.run() completed - this shouldn't happen unless connection closed")
                except KeyboardInterrupt:
                    logger.info("Server interrupted by user")
                    raise
                except Exception as run_error:
                    logger.error(f"Error in server.run(): {run_error}", exc_info=True)
                    # Don't re-raise - let cleanup happen
                    raise
        except Exception as e:
            logger.error(f"Error running PM MCP Server: {e}", exc_info=True)
            raise
        finally:
            self._cleanup()
    
    async def run_sse(self) -> None:
        """
        Run server with SSE (Server-Sent Events) transport.
        
        This transport is suitable for web-based agents.
        """
        logger.info(
            f"Starting PM MCP Server with SSE transport on {self.config.host}:{self.config.port}..."
        )
        
        try:
            # Initialize PM Handler
            self._initialize_pm_handler()
            
            # Register all tools
            self._register_all_tools()
            
            # Create FastAPI app with SSE endpoints
            from .transports.sse import create_sse_app
            
            app = create_sse_app(self.pm_handler, self.config, mcp_server_instance=self)
            
            # Tools are automatically handled by the MCP server through the SSE transport
            # The new SSE implementation uses EventSourceResponse and memory streams
            # All tool calls are routed through the MCP server's native handlers
            logger.info(f"SSE transport initialized - {len(self._tool_names)} tools available via MCP server")
            
            # Import uvicorn for running FastAPI
            import uvicorn
            
            logger.info(
                f"PM MCP Server (SSE) starting on http://{self.config.host}:{self.config.port}"
            )
            logger.info(f"SSE endpoint: http://{self.config.host}:{self.config.port}/sse")
            logger.info(f"Tools endpoint: http://{self.config.host}:{self.config.port}/tools/list")
            logger.info(f"Call tool: http://{self.config.host}:{self.config.port}/tools/call")
            logger.info(f"Stream tool: http://{self.config.host}:{self.config.port}/tools/call/stream")
            
            # Run uvicorn server
            config_uvicorn = uvicorn.Config(
                app,
                host=self.config.host,
                port=self.config.port,
                log_level=self.config.log_level.lower(),
                access_log=True,
            )
            server = uvicorn.Server(config_uvicorn)
            await server.serve()
            
        except Exception as e:
            logger.error(f"Error running PM MCP Server: {e}")
            raise
        finally:
            self._cleanup()
    
    async def run_http(self) -> None:
        """
        Run server with HTTP transport.
        
        This transport provides RESTful API access to MCP tools.
        """
        logger.info(
            f"Starting PM MCP Server with HTTP transport on {self.config.host}:{self.config.port}..."
        )
        
        try:
            # Initialize PM Handler
            self._initialize_pm_handler()
            
            # Register all tools
            self._register_all_tools()
            
            # Create FastAPI app with HTTP REST API
            from .transports.http import create_http_app
            
            app = create_http_app(self.pm_handler, self.config)
            
            # Import uvicorn for running FastAPI
            import uvicorn
            
            logger.info(
                f"PM MCP Server (HTTP) starting on http://{self.config.host}:{self.config.port}"
            )
            logger.info(f"API Documentation: http://{self.config.host}:{self.config.port}/docs")
            logger.info(f"ReDoc: http://{self.config.host}:{self.config.port}/redoc")
            logger.info(f"Health: http://{self.config.host}:{self.config.port}/health")
            logger.info(f"Tools: http://{self.config.host}:{self.config.port}/tools")
            logger.info(f"Projects: http://{self.config.host}:{self.config.port}/projects")
            logger.info(f"Tasks: http://{self.config.host}:{self.config.port}/tasks/my")
            
            # Run uvicorn server
            config_uvicorn = uvicorn.Config(
                app,
                host=self.config.host,
                port=self.config.port,
                log_level=self.config.log_level.lower(),
                access_log=True,
            )
            server = uvicorn.Server(config_uvicorn)
            await server.serve()
            
        except Exception as e:
            logger.error(f"Error running PM MCP Server: {e}")
            raise
        finally:
            self._cleanup()
    
    def _cleanup(self) -> None:
        """Clean up resources."""
        logger.info("Cleaning up PM MCP Server...")
        
        if self.db_session:
            self.db_session.close()
            self.db_session = None
        
        self.pm_handler = None
        
        logger.info("PM MCP Server stopped")
    
    async def run(self) -> None:
        """
        Run server with configured transport.
        
        This is the main entry point that dispatches to the appropriate transport.
        """
        if self.config.transport == "stdio":
            await self.run_stdio()
        elif self.config.transport == "sse":
            await self.run_sse()
        elif self.config.transport == "http":
            await self.run_http()
        else:
            raise ValueError(f"Unknown transport: {self.config.transport}")

