"""
SSE (Server-Sent Events) Transport for PM MCP Server

Provides HTTP/SSE endpoint for web-based agents to connect to PM MCP Server.
"""

import json
import logging
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.server.pm_handler import PMHandler
from ..config import PMServerConfig

logger = logging.getLogger(__name__)


class MCPRequest(BaseModel):
    """MCP tool call request."""
    tool: str
    arguments: dict[str, Any]
    request_id: str | None = None


class MCPListToolsRequest(BaseModel):
    """Request to list available tools."""
    pass


def create_sse_app(pm_handler: PMHandler, config: PMServerConfig, mcp_server_instance=None) -> FastAPI:
    """
    Create FastAPI application with SSE endpoint for PM MCP Server.
    
    Args:
        pm_handler: PM handler instance
        config: Server configuration
        mcp_server_instance: Optional PMMCPServer instance to access MCP tools
    
    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="PM MCP Server (SSE)",
        description="Project Management MCP Server with SSE transport",
        version=config.server_version
    )
    
    # Store MCP server instance for accessing tools
    app.state.mcp_server = mcp_server_instance
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure based on config in production
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Store PM handler in app state
    app.state.pm_handler = pm_handler
    app.state.config = config
    
    # Tool registry (populated when tools are registered)
    app.state.tools = {}
    
    def _make_sse_event(event_type: str, data: dict[str, Any]) -> str:
        """Format data as SSE event."""
        try:
            json_data = json.dumps(data, ensure_ascii=False)
            return f"event: {event_type}\ndata: {json_data}\n\n"
        except Exception as e:
            logger.error(f"Error formatting SSE event: {e}")
            return f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
    
    @app.get("/")
    async def root():
        """Root endpoint with server info."""
        return {
            "name": config.server_name,
            "version": config.server_version,
            "transport": "sse",
            "status": "running",
            "tools_count": len(app.state.tools),
        }
    
    @app.get("/health")
    async def health():
        """Health check endpoint."""
        try:
            # Check if PM handler is working
            providers = pm_handler._get_active_providers()
            return {
                "status": "healthy",
                "providers": len(providers),
                "tools": len(app.state.tools),
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise HTTPException(status_code=503, detail=f"Unhealthy: {str(e)}")
    
    @app.post("/tools/list")
    async def list_tools(request: MCPListToolsRequest | None = None):
        """List all available MCP tools."""
        try:
            # Try to get tools from MCP server instance if available
            if hasattr(app.state, 'mcp_server') and app.state.mcp_server:
                from mcp.types import ListToolsRequest
                # Call the MCP server's list_tools handler
                handler = app.state.mcp_server.server.request_handlers.get(ListToolsRequest)
                if handler:
                    result = await handler(ListToolsRequest(params=None))
                    # Extract tools from ListToolsResult
                    if hasattr(result, 'tools'):
                        tools = result.tools
                    elif hasattr(result, 'model_dump'):
                        dump = result.model_dump()
                        tools = dump.get('tools', [])
                    else:
                        tools = []
                    
                    # Convert to dict format for SSE endpoint
                    tools_list = []
                    for tool in tools:
                        tool_dict = {
                            "name": tool.name if hasattr(tool, 'name') else tool.get('name', ''),
                            "description": tool.description if hasattr(tool, 'description') else tool.get('description', ''),
                        }
                        if hasattr(tool, 'inputSchema'):
                            tool_dict["inputSchema"] = tool.inputSchema
                        elif isinstance(tool, dict) and 'inputSchema' in tool:
                            tool_dict["inputSchema"] = tool['inputSchema']
                        tools_list.append(tool_dict)
                    
                    return {
                        "tools": tools_list,
                        "count": len(tools_list),
                    }
            
            # Fallback to app.state.tools if MCP server not available
            tools_list = [
                {
                    "name": name,
                    "description": tool_info.get("description", ""),
                    "parameters": tool_info.get("parameters", {}),
                }
                for name, tool_info in getattr(app.state, 'tools', {}).items()
            ]
            
            return {
                "tools": tools_list,
                "count": len(tools_list),
            }
        except Exception as e:
            logger.error(f"Error listing tools: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/tools/call")
    async def call_tool(request: MCPRequest):
        """
        Call an MCP tool and return results.
        
        This is a non-streaming endpoint for simple tool calls.
        """
        try:
            tool_name = request.tool
            arguments = request.arguments
            
            logger.info(f"Tool call: {tool_name} with args: {arguments}")
            
            # Get tool from registry
            if tool_name not in app.state.tools:
                raise HTTPException(
                    status_code=404,
                    detail=f"Tool '{tool_name}' not found"
                )
            
            tool_func = app.state.tools[tool_name]["function"]
            
            # Execute tool
            result = await tool_func(arguments)
            
            # Format response
            return {
                "request_id": request.request_id,
                "tool": tool_name,
                "result": result,
                "success": True,
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error calling tool {request.tool}: {e}", exc_info=True)
            return {
                "request_id": request.request_id,
                "tool": request.tool,
                "error": str(e),
                "success": False,
            }
    
    @app.post("/tools/call/stream")
    async def call_tool_stream(request: MCPRequest):
        """
        Call an MCP tool and stream results via SSE.
        
        This endpoint streams tool execution progress and results.
        """
        async def event_generator() -> AsyncGenerator[str, None]:
            try:
                tool_name = request.tool
                arguments = request.arguments
                request_id = request.request_id or "unknown"
                
                logger.info(f"Streaming tool call: {tool_name}")
                
                # Send start event
                yield _make_sse_event("start", {
                    "request_id": request_id,
                    "tool": tool_name,
                    "status": "executing"
                })
                
                # Get tool from registry
                if tool_name not in app.state.tools:
                    yield _make_sse_event("error", {
                        "request_id": request_id,
                        "error": f"Tool '{tool_name}' not found"
                    })
                    return
                
                tool_func = app.state.tools[tool_name]["function"]
                
                # Execute tool
                result = await tool_func(arguments)
                
                # Send result event
                yield _make_sse_event("result", {
                    "request_id": request_id,
                    "tool": tool_name,
                    "result": result,
                    "success": True
                })
                
                # Send completion event
                yield _make_sse_event("complete", {
                    "request_id": request_id,
                    "status": "completed"
                })
                
            except Exception as e:
                logger.error(f"Error in streaming tool call: {e}", exc_info=True)
                yield _make_sse_event("error", {
                    "request_id": request.request_id or "unknown",
                    "error": str(e)
                })
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )
    
    @app.get("/sse")
    async def sse_endpoint():
        """
        Main SSE endpoint for MCP protocol communication.
        
        This endpoint maintains a persistent connection and handles
        bidirectional communication via SSE.
        """
        async def event_generator() -> AsyncGenerator[str, None]:
            try:
                # Send connection established event
                yield _make_sse_event("connected", {
                    "server": config.server_name,
                    "version": config.server_version,
                    "tools_count": len(app.state.tools),
                })
                
                # Send tools list
                tools_list = [
                    {
                        "name": name,
                        "description": tool_info.get("description", ""),
                    }
                    for name, tool_info in app.state.tools.items()
                ]
                
                yield _make_sse_event("tools", {
                    "tools": tools_list,
                    "count": len(tools_list),
                })
                
                # Keep connection alive
                # In a real implementation, this would handle incoming messages
                # For now, we'll keep the connection open
                logger.info("SSE connection established")
                
                # Send heartbeat every 30 seconds
                import asyncio
                while True:
                    await asyncio.sleep(30)
                    yield _make_sse_event("heartbeat", {
                        "timestamp": str(asyncio.get_event_loop().time())
                    })
                    
            except Exception as e:
                logger.error(f"Error in SSE endpoint: {e}", exc_info=True)
                yield _make_sse_event("error", {"error": str(e)})
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )
    
    return app


def register_tool_with_sse(
    app: FastAPI,
    tool_name: str,
    tool_func: Any,
    description: str = "",
    parameters: dict[str, Any] | None = None
):
    """
    Register a tool with the SSE app.
    
    Args:
        app: FastAPI application
        tool_name: Name of the tool
        tool_func: Tool function (async callable)
        description: Tool description
        parameters: Tool parameters schema
    """
    app.state.tools[tool_name] = {
        "function": tool_func,
        "description": description,
        "parameters": parameters or {},
    }
    logger.debug(f"Registered tool: {tool_name}")

