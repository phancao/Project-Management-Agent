"""
HTTP Transport for MCP Meeting Server.

Provides REST API transport for direct tool access.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class ToolCallRequest(BaseModel):
    """Request body for tool calls"""
    name: str
    arguments: Dict[str, Any] = {}


class ToolCallResponse(BaseModel):
    """Response from tool calls"""
    success: bool
    result: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


def create_http_app(mcp_server) -> FastAPI:
    """
    Create a FastAPI app with HTTP transport.
    
    Args:
        mcp_server: The MeetingMCPServer instance
        
    Returns:
        FastAPI application
    """
    app = FastAPI(
        title="Meeting MCP Server - HTTP API",
        description="HTTP API for meeting processing tools",
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
    
    @app.get("/tools/list")
    async def list_tools():
        """List all available tools"""
        from mcp_meeting_server.tools import register_all_tools
        
        # Get tool list - this is a simplified approach
        return {
            "tools": [
                {
                    "name": "upload_meeting",
                    "description": "Upload a meeting recording for processing"
                },
                {
                    "name": "process_meeting",
                    "description": "Process an uploaded meeting"
                },
                {
                    "name": "analyze_transcript",
                    "description": "Analyze a text transcript"
                },
                {
                    "name": "get_meeting_summary",
                    "description": "Get meeting summary"
                },
                {
                    "name": "list_action_items",
                    "description": "List action items from meeting"
                },
                {
                    "name": "create_tasks_from_meeting",
                    "description": "Create PM tasks from action items"
                },
                {
                    "name": "list_meetings",
                    "description": "List all meetings"
                },
            ]
        }
    
    @app.post("/tools/call", response_model=ToolCallResponse)
    async def call_tool(request: ToolCallRequest):
        """Call a tool by name"""
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
    
    # Convenience endpoints for common operations
    
    @app.post("/meetings/analyze-transcript")
    async def analyze_transcript(
        transcript: str,
        title: str = "Meeting",
        participants: List[str] = [],
        project_id: Optional[str] = None,
    ):
        """Analyze a transcript directly"""
        from mcp_meeting_server.tools import _handle_analyze_transcript
        
        result = await _handle_analyze_transcript(mcp_server, {
            "transcript": transcript,
            "title": title,
            "participants": participants,
            "project_id": project_id,
        })
        
        return {"result": result}
    
    @app.get("/meetings")
    async def list_meetings(status: str = "all", limit: int = 20):
        """List all meetings"""
        from mcp_meeting_server.tools import _handle_list_meetings
        
        result = await _handle_list_meetings(mcp_server, {
            "status": status,
            "limit": limit,
        })
        
        return {"result": result}
    
    return app
