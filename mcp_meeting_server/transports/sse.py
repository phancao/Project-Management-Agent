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
    
    return app
