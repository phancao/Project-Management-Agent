"""
SSE Transport for MCP Meeting Server.

Provides Server-Sent Events transport for web-based agents.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
import logging

logger = logging.getLogger(__name__)


def create_sse_app(mcp_server) -> FastAPI:
    """
    Create a FastAPI app with SSE transport.
    
    Args:
        mcp_server: The MeetingMCPServer instance
        
    Returns:
        FastAPI application
    """
    app = FastAPI(
        title="Meeting MCP Server",
        description="MCP Server for meeting processing",
        version="1.0.0",
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/health")
    async def health():
        """Health check endpoint"""
        return {"status": "healthy", "service": "meeting-mcp-server"}
    
    @app.get("/sse")
    async def sse_endpoint(request: Request):
        """SSE endpoint for MCP protocol"""
        try:
            # Create SSE transport
            from mcp.server.sse import SseServerTransport
            
            transport = SseServerTransport("/sse")
            
            async def generate():
                async with transport.connect_sse(
                    request.scope,
                    request.receive,
                    request._send
                ) as (read, write):
                    await mcp_server._server.run(
                        read,
                        write,
                        mcp_server._server.create_initialization_options()
                    )
            
            return EventSourceResponse(generate())
            
        except Exception as e:
            logger.exception(f"SSE connection failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/messages")
    async def messages_endpoint(request: Request):
        """Handle MCP messages via HTTP POST"""
        # This is a simplified implementation
        # In production, use proper MCP transport
        body = await request.json()
        
        return {
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "result": {"status": "ok"}
        }

    # HTTP Tool Access (Hybrid Mode)
    from mcp_meeting_server.transports.http import ToolCallRequest, ToolCallResponse
    
    @app.post("/tools/call", response_model=ToolCallResponse)
    async def call_tool(request: ToolCallRequest):
        """Call a tool by name (HTTP override)"""
        try:
            from mcp_meeting_server.tools import (
                _handle_upload_meeting,
                _handle_process_meeting,
                _handle_analyze_transcript,
                _handle_get_summary,
                _handle_list_action_items,
                _handle_create_tasks,
                _handle_list_meetings,
            )
            
            handlers = {
                "upload_meeting": _handle_upload_meeting,
                "process_meeting": _handle_process_meeting,
                "analyze_transcript": _handle_analyze_transcript,
                "get_meeting_summary": _handle_get_summary,
                "list_action_items": _handle_list_action_items,
                "create_tasks_from_meeting": _handle_create_tasks,
                "list_meetings": _handle_list_meetings,
            }
            
            if request.name not in handlers:
                return ToolCallResponse(
                    success=False,
                    error=f"Unknown tool: {request.name}"
                )
            
            handler = handlers[request.name]
            result = await handler(mcp_server, request.arguments)
            
            return ToolCallResponse(success=True, result=result)
            
        except Exception as e:
            logger.exception(f"Tool call failed: {e}")
            return ToolCallResponse(success=False, error=str(e))

    @app.get("/meetings")
    async def list_meetings(status: str = "all", limit: int = 20, projectId: str = None):
        """List all meetings"""
        from mcp_meeting_server.tools import _handle_list_meetings
        
        args = {
            "status": status,
            "limit": limit,
        }
        if projectId:
            args["project_id"] = projectId

        result = await _handle_list_meetings(mcp_server, args)
        
        # Ensure result has matching key 'meetings' or wrap it
        return result if "meetings" in result else {"meetings": result}

    @app.get("/users")
    async def list_users(projectId: str = None, limit: int = 100):
        """List users from PM tools"""
        from mcp_meeting_server.tools import _handle_list_users
        
        args = {
            "limit": limit
        }
        if projectId:
            args["project_id"] = projectId
            
        result = await _handle_list_users(mcp_server, args)
        return result

    return app
