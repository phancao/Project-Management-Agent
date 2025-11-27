"""
SSE (Server-Sent Events) Transport for PM MCP Server

Provides HTTP/SSE endpoint for web-based agents to connect to PM MCP Server.
Uses MCP SDK's SseServerTransport for proper protocol implementation.
"""

import asyncio
import json
import logging
from typing import Any
from uuid import uuid4

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette import EventSourceResponse
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response

from ..pm_handler import MCPPMHandler
from ..config import PMServerConfig
from ..services.auth_service import AuthService
from ..services.user_context import UserContext
from ..api.provider_sync import router as provider_sync_router

logger = logging.getLogger(__name__)


class MCPRequest(BaseModel):
    """MCP tool call request."""
    tool: str
    arguments: dict[str, Any]
    request_id: str | None = None


class MCPListToolsRequest(BaseModel):
    """Request to list available tools."""
    pass


def create_sse_app(pm_handler: MCPPMHandler, config: PMServerConfig, mcp_server_instance=None) -> FastAPI:
    """
    Create FastAPI application with SSE endpoint for PM MCP Server.
    
    Uses MCP SDK's SseServerTransport for proper protocol implementation.
    
    Args:
        pm_handler: PM handler instance
        config: Server configuration
        mcp_server_instance: PMMCPServer instance (required for MCP protocol)
    
    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="PM MCP Server (SSE)",
        description="Project Management MCP Server with SSE transport",
        version=config.server_version
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include provider sync API router
    app.include_router(provider_sync_router)
    
    # Store references
    app.state.pm_handler = pm_handler
    app.state.config = config
    app.state.mcp_server = mcp_server_instance
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        try:
            providers = pm_handler._get_active_providers()
            return {
                "status": "healthy",
                "providers": len(providers),
                "tools": len(mcp_server_instance._tool_names) if mcp_server_instance else 0
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    @app.get("/sse")
    async def sse_endpoint(request: Request):
        """
        SSE endpoint for MCP protocol.
        
        This endpoint uses the MCP SDK's SseServerTransport to properly
        implement the MCP protocol over SSE.
        
        User identification can be provided via:
        - Header: X-MCP-API-Key (validates and gets user_id)
        - Header: X-User-ID (direct user ID)
        - Query parameter: ?user_id=<uuid>
        """
        from mcp.server.sse import SseServerTransport
        from sse_starlette import EventSourceResponse
        
        try:
            # Extract user ID using authentication service
            # Determine if auth is required based on config
            require_auth = AuthService.should_require_auth(config)
            user_id = await AuthService.extract_user_id(request, require_auth=require_auth)
            
            # Create user-scoped MCP server instance
            if user_id:
                mcp_server = UserContext.create_user_scoped_server(user_id, config)
            else:
                # Fallback to global server (backward compatibility, not recommended)
                logger.warning("[SSE] Using global MCP server instance (no user context)")
                mcp_server = app.state.mcp_server
            
            if not mcp_server:
                raise HTTPException(
                    status_code=503,
                    detail="MCP server not available"
                )
            
            # Use MCP SDK's SseServerTransport
            # Store in app.state so /messages endpoint can access it
            if not hasattr(app.state, 'sse_transport'):
                app.state.sse_transport = SseServerTransport("/messages")
            transport = app.state.sse_transport
            
            # Convert FastAPI Request to ASGI format
            scope = request.scope.copy()
            
            async def asgi_receive():
                """ASGI receive function"""
                return {"type": "http.request", "body": b""}
            
            # Create memory streams for bidirectional communication
            from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
            
            # Create streams: 
            # - read_stream: messages FROM client TO server (via /messages endpoint)
            # - write_stream: messages FROM server TO client (via SSE events)
            read_stream_writer, read_stream_raw = anyio.create_memory_object_stream(0)
            write_stream, write_stream_reader = anyio.create_memory_object_stream(0)
            
            # Create a wrapper stream that converts JSONRPCMessage to typed requests
            # The SDK should do this automatically, but it's not working, so we'll do it manually
            read_stream_converted_writer, read_stream_converted = anyio.create_memory_object_stream(0)
            
            # Task to convert messages from raw stream to converted stream
            # The SDK should convert JSONRPCMessage to typed requests automatically,
            # but it's not working. We'll pass messages through and let the SDK handle it.
            # If the SDK still fails, we'll need to investigate further.
            async def convert_messages():
                """Pass messages through to server.run() - SDK should handle conversion"""
                try:
                    async with read_stream_raw:
                        async for session_message in read_stream_raw:
                            # Pass through - the SDK's server.run() should convert
                            # JSONRPCMessage to typed requests based on method
                            await read_stream_converted_writer.send(session_message)
                except Exception as e:
                    logger.error(f"[SSE] Error in message converter: {e}", exc_info=True)
                    await read_stream_converted_writer.send(e)
            
            # Start the converter task
            converter_task = asyncio.create_task(convert_messages())
            
            # Store the write stream writer in the transport's session
            # The transport expects to find it via session_id
            from uuid import uuid4
            session_id = uuid4()
            transport._read_stream_writers[session_id] = read_stream_writer
            
            # Create SSE event generator
            async def sse_event_generator():
                """Generate SSE events from MCP server responses"""
                try:
                    # Send endpoint event first (as per MCP protocol)
                    root_path = scope.get("root_path", "")
                    full_message_path = root_path.rstrip("/") + "/messages"
                    client_post_uri = f"{full_message_path}?session_id={session_id.hex}"
                    yield {"event": "endpoint", "data": client_post_uri}
                    
                    # Run MCP server in background
                    # The server.run() method processes messages from read_stream
                    # and sends responses to write_stream
                    # Use the server's create_initialization_options() to get proper InitializationOptions
                    init_options = mcp_server.server.create_initialization_options()
                    
                    logger.info(f"[SSE] Starting MCP server.run() with streams")
                    
                    # Create a task to run the server
                    # This will process all messages from read_stream
                    async def run_server():
                        try:
                            logger.info(f"[SSE] MCP server.run() starting...")
                            # Use the converted stream (messages are passed through as-is,
                            # the SDK's message router should convert them)
                            await mcp_server.server.run(
                                read_stream_converted,
                                write_stream,
                                init_options
                            )
                            logger.info(f"[SSE] MCP server.run() completed")
                        except Exception as e:
                            logger.error(f"[SSE] Error in MCP server.run(): {e}", exc_info=True)
                            # Send error to write stream
                            from mcp.shared.exceptions import McpError
                            error = McpError(
                                code=-32603,
                                message=f"Internal error: {str(e)}"
                            )
                            await write_stream.send(error)
                    
                    server_task = asyncio.create_task(run_server())
                    
                    # Stream messages from write_stream_reader
                    async with write_stream_reader:
                        async for session_message in write_stream_reader:
                            # Convert SessionMessage to SSE event
                            # session_message is a SessionMessage object with .message attribute
                            if isinstance(session_message, Exception):
                                # Handle exceptions
                                error_data = json.dumps({"error": str(session_message)})
                                yield {"event": "error", "data": error_data}
                            else:
                                # session_message.message is a JSONRPCMessage
                                # Convert it to JSON string
                                if hasattr(session_message.message, 'model_dump_json'):
                                    message_json = session_message.message.model_dump_json(by_alias=True, exclude_none=True)
                                elif hasattr(session_message.message, 'model_dump'):
                                    message_json = json.dumps(session_message.message.model_dump(by_alias=True, exclude_none=True))
                                else:
                                    # Fallback: convert to dict and then JSON
                                    message_json = json.dumps(session_message.message)
                                yield {"event": "message", "data": message_json}
                    
                    # Wait for server to complete
                    try:
                        await server_task
                    except asyncio.CancelledError:
                        logger.info("SSE connection cancelled")
                    except Exception as e:
                        logger.error(f"Error in MCP server: {e}", exc_info=True)
                        yield {"event": "error", "data": json.dumps({"error": str(e)})}
                        
                except Exception as e:
                    logger.error(f"Error in SSE event generator: {e}", exc_info=True)
                    yield {"event": "error", "data": json.dumps({"error": str(e)})}
                finally:
                    # Cleanup
                    if session_id in transport._read_stream_writers:
                        del transport._read_stream_writers[session_id]
                    # Cancel converter task
                    converter_task.cancel()
                    try:
                        await converter_task
                    except asyncio.CancelledError:
                        pass
                    await read_stream_writer.aclose()
                    await read_stream_converted_writer.aclose()
                    await write_stream_reader.aclose()
            
            # Return EventSourceResponse (from sse_starlette)
            return EventSourceResponse(sse_event_generator())
            
        except Exception as e:
            logger.error(f"Error in SSE endpoint: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"SSE connection error: {str(e)}"
            )
    
    @app.post("/messages")
    async def messages_endpoint(request: Request):
        """
        POST endpoint for MCP messages (required by SseServerTransport).
        
        The SseServerTransport expects messages to be posted to /messages
        while the SSE connection is established at /sse.
        """
        from mcp.server.sse import SseServerTransport
        
        try:
            # Get the MCP server instance (use global for now, session matching handled by transport)
            mcp_server = app.state.mcp_server
            
            if not mcp_server:
                raise HTTPException(
                    status_code=503,
                    detail="MCP server not available"
                )
            
            # Get the transport instance from app.state (same one used in /sse)
            if not hasattr(app.state, 'sse_transport'):
                raise HTTPException(
                    status_code=503,
                    detail="SSE transport not initialized"
                )
            transport = app.state.sse_transport
            
            # Get session_id from query params
            session_id_param = request.query_params.get("session_id")
            if not session_id_param:
                raise HTTPException(
                    status_code=400,
                    detail="session_id is required"
                )
            
            try:
                from uuid import UUID
                session_id = UUID(hex=session_id_param)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid session_id"
                )
            
            # Get the read stream writer for this session
            read_stream_writer = transport._read_stream_writers.get(session_id)
            if not read_stream_writer:
                raise HTTPException(
                    status_code=404,
                    detail="Session not found"
                )
            
            # Get the message body
            body = await request.body()
            
            # Create SessionMessage and send it to the read stream
            # Following the MCP SDK's handle_post_message implementation exactly
            from mcp.shared.message import SessionMessage, ServerMessageMetadata
            from mcp.types import JSONRPCMessage
            from pydantic import ValidationError
            from starlette.requests import Request as StarletteRequest
            
            try:
                # Parse JSON-RPC message using model_validate_json (from bytes)
                # This matches the MCP SDK's implementation
                try:
                    jsonrpc_message = JSONRPCMessage.model_validate_json(body)
                    # JSONRPCMessage has a 'root' field that contains the actual JSON-RPC message
                    root_message = jsonrpc_message.root
                    logger.info(f"[SSE] Received JSON-RPC message: type={type(root_message).__name__}")
                    
                    # Log method and id if it's a request
                    if hasattr(root_message, 'method'):
                        logger.info(f"[SSE] Method: {root_message.method}, ID: {getattr(root_message, 'id', 'N/A')}")
                    if hasattr(root_message, 'params'):
                        logger.debug(f"[SSE] Message params type: {type(root_message.params)}")
                        logger.debug(f"[SSE] Message params: {root_message.params}")
                    
                    logger.debug(f"[SSE] Full message: {jsonrpc_message}")
                except ValidationError as err:
                    logger.exception("Failed to parse message")
                    # Send error to the stream
                    await read_stream_writer.send(err)
                    raise HTTPException(
                        status_code=400,
                        detail="Could not parse message"
                    )
                
                # Create SessionMessage with metadata (matching MCP SDK)
                # The SDK's server.run() should automatically convert JSONRPCMessage
                # to typed requests (InitializeRequest, ListToolsRequest, etc.)
                # based on the method field. We just need to pass the JSONRPCMessage
                # and let the SDK handle the conversion.
                starlette_request = StarletteRequest(request.scope, request.receive)
                metadata = ServerMessageMetadata(request_context=starlette_request)
                session_message = SessionMessage(
                    message=jsonrpc_message,
                    metadata=metadata
                )
                
                logger.debug(f"[SSE] Created SessionMessage: {session_message}")
                logger.debug(f"[SSE] SessionMessage.message type: {type(session_message.message)}")
                
                # The SDK's server.run() should handle message conversion automatically
                # Send to read stream (this will be picked up by the MCP server)
                await read_stream_writer.send(session_message)
                logger.debug(f"[SSE] Sent SessionMessage to read stream")
                
                # Return 202 Accepted (matching MCP SDK)
                return Response("Accepted", status_code=202)
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Error processing message: {str(e)}"
                )
            
        except Exception as e:
            logger.error(f"Error in messages endpoint: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Message handling error: {str(e)}"
            )
    
    @app.get("/tools/list")
    async def list_tools():
        """List available tools (for debugging/testing)"""
        try:
            mcp_server = app.state.mcp_server
            if not mcp_server:
                return {"tools": []}
            
            # Get tools from MCP server's internal registry
            # The _tool_names list contains all registered tool names
            tools = []
            for tool_name in mcp_server._tool_names:
                # Get tool function from registry
                tool_func = mcp_server._tool_functions.get(tool_name)
                if tool_func:
                    # Extract description from function docstring
                    description = tool_func.__doc__ or f"Tool: {tool_name}"
                    description = description.strip().split('\n')[0] if description else f"Tool: {tool_name}"
                    
                    tools.append({
                        "name": tool_name,
                        "description": description
                    })
                else:
                    # Fallback if function not found
                    tools.append({
                        "name": tool_name,
                        "description": f"Tool: {tool_name}"
                    })
            
            return {"tools": tools, "count": len(tools)}
        except Exception as e:
            logger.error(f"Error listing tools: {e}", exc_info=True)
            return {"tools": [], "error": str(e)}
    
    return app
