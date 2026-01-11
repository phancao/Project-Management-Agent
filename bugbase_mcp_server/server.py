# Copyright (c) 2025 Galaxy Technology Service
# BugBase MCP Server - Main Server Entry Point

import os
import logging
import base64
import uuid
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent

from database import get_db, init_db, Bug, BugComment

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bugbase")

# FastAPI app for REST API + SSE transport
app = FastAPI(title="BugBase MCP Server", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MCP Server
mcp_server = Server("bugbase")

# Screenshot storage path
SCREENSHOT_DIR = Path(os.getenv("SCREENSHOT_DIR", "/app/uploads/screenshots"))
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


# ============ REST API Models ============

class CreateBugRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    severity: str = Field(default="medium")
    screenshot_base64: Optional[str] = None
    navigation_history: Optional[List[dict]] = None
    page_url: Optional[str] = None
    user_agent: Optional[str] = None


class UpdateBugStatusRequest(BaseModel):
    status: str = Field(..., pattern="^(open|in_progress|fixed|closed)$")


class AddCommentRequest(BaseModel):
    content: str = Field(..., min_length=1)
    author: str = Field(default="user")


# ============ REST API Endpoints ============

@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    init_db()
    logger.info("BugBase MCP Server started")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "bugbase"}


@app.get("/api/screenshots/{filename}")
async def get_screenshot(filename: str):
    """Serve screenshot images."""
    from fastapi.responses import FileResponse
    
    # Security: only allow .png files and prevent path traversal
    if not filename.endswith(".png") or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    filepath = SCREENSHOT_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Screenshot not found")
    
    return FileResponse(filepath, media_type="image/png")


@app.post("/api/bugs")
async def create_bug(request: CreateBugRequest):
    """Create a new bug report."""
    with get_db() as db:
        # Save screenshot if provided
        screenshot_path = None
        if request.screenshot_base64:
            try:
                # Remove data URL prefix if present
                base64_data = request.screenshot_base64
                if "," in base64_data:
                    base64_data = base64_data.split(",")[1]
                
                # Decode and save
                image_data = base64.b64decode(base64_data)
                filename = f"{uuid.uuid4()}.png"
                filepath = SCREENSHOT_DIR / filename
                filepath.write_bytes(image_data)
                screenshot_path = str(filepath)
            except Exception as e:
                logger.warning(f"Failed to save screenshot: {e}")

        # Create bug
        bug = Bug(
            title=request.title,
            description=request.description,
            severity=request.severity,
            screenshot_path=screenshot_path,
            navigation_history=request.navigation_history,
            page_url=request.page_url,
            user_agent=request.user_agent,
        )
        db.add(bug)
        db.commit()
        db.refresh(bug)
        
        logger.info(f"Created bug: {bug.id} - {bug.title}")
        return bug.to_dict()


@app.get("/api/bugs")
async def list_bugs(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """List bugs with optional filters."""
    with get_db() as db:
        query = db.query(Bug)
        
        if status:
            query = query.filter(Bug.status == status)
        if severity:
            query = query.filter(Bug.severity == severity)
        
        total = query.count()
        bugs = query.order_by(Bug.created_at.desc()).offset(offset).limit(limit).all()
        
        return {
            "total": total,
            "bugs": [b.to_dict() for b in bugs],
        }


@app.get("/api/bugs/{bug_id}")
async def get_bug(bug_id: str):
    """Get bug details with comments."""
    with get_db() as db:
        bug = db.query(Bug).filter(Bug.id == bug_id).first()
        if not bug:
            raise HTTPException(status_code=404, detail="Bug not found")
        return bug.to_dict(include_comments=True)


@app.patch("/api/bugs/{bug_id}/status")
async def update_bug_status(bug_id: str, request: UpdateBugStatusRequest):
    """Update bug status."""
    with get_db() as db:
        bug = db.query(Bug).filter(Bug.id == bug_id).first()
        if not bug:
            raise HTTPException(status_code=404, detail="Bug not found")
        
        bug.status = request.status
        db.commit()
        db.refresh(bug)
        
        logger.info(f"Updated bug {bug_id} status to {request.status}")
        return bug.to_dict()


@app.post("/api/bugs/{bug_id}/comments")
async def add_comment(bug_id: str, request: AddCommentRequest):
    """Add a comment to a bug."""
    with get_db() as db:
        bug = db.query(Bug).filter(Bug.id == bug_id).first()
        if not bug:
            raise HTTPException(status_code=404, detail="Bug not found")
        
        comment = BugComment(
            bug_id=bug.id,
            content=request.content,
            author=request.author,
        )
        db.add(comment)
        db.commit()
        db.refresh(comment)
        
        logger.info(f"Added comment to bug {bug_id}")
        return comment.to_dict()


# ============ MCP Tools ============

@mcp_server.list_tools()
async def list_tools():
    """List available MCP tools."""
    return [
        Tool(
            name="list_bugs",
            description="List all bug reports with optional filters. Returns bugs sorted by creation date (newest first).",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["open", "in_progress", "fixed", "closed"],
                        "description": "Filter by bug status",
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                        "description": "Filter by severity level",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 20,
                        "description": "Maximum number of bugs to return",
                    },
                },
            },
        ),
        Tool(
            name="get_bug_details",
            description="Get detailed information about a specific bug including screenshot path, navigation history, and comments.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bug_id": {
                        "type": "string",
                        "description": "The UUID of the bug to retrieve",
                    },
                },
                "required": ["bug_id"],
            },
        ),
        Tool(
            name="update_bug_status",
            description="Update the status of a bug (e.g., mark as in_progress, fixed, or closed).",
            inputSchema={
                "type": "object",
                "properties": {
                    "bug_id": {
                        "type": "string",
                        "description": "The UUID of the bug to update",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["open", "in_progress", "fixed", "closed"],
                        "description": "The new status",
                    },
                },
                "required": ["bug_id", "status"],
            },
        ),
        Tool(
            name="add_bug_comment",
            description="Add a comment to a bug for investigation notes or resolution details.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bug_id": {
                        "type": "string",
                        "description": "The UUID of the bug",
                    },
                    "content": {
                        "type": "string",
                        "description": "The comment content",
                    },
                },
                "required": ["bug_id", "content"],
            },
        ),
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Execute MCP tool."""
    try:
        if name == "list_bugs":
            status = arguments.get("status")
            severity = arguments.get("severity")
            limit = arguments.get("limit", 20)
            
            with get_db() as db:
                query = db.query(Bug)
                if status:
                    query = query.filter(Bug.status == status)
                if severity:
                    query = query.filter(Bug.severity == severity)
                
                bugs = query.order_by(Bug.created_at.desc()).limit(limit).all()
                
                result = f"Found {len(bugs)} bug(s):\n\n"
                for bug in bugs:
                    result += f"- [{bug.severity.upper()}] {bug.title}\n"
                    result += f"  ID: {bug.id}\n"
                    result += f"  Status: {bug.status}\n"
                    result += f"  URL: {bug.page_url or 'N/A'}\n"
                    result += f"  Created: {bug.created_at}\n\n"
                
                return [TextContent(type="text", text=result)]

        elif name == "get_bug_details":
            bug_id = arguments.get("bug_id")
            
            with get_db() as db:
                bug = db.query(Bug).filter(Bug.id == bug_id).first()
                if not bug:
                    return [TextContent(type="text", text=f"Bug not found: {bug_id}")]
                
                result = f"Bug Details:\n"
                result += f"============\n"
                result += f"Title: {bug.title}\n"
                result += f"ID: {bug.id}\n"
                result += f"Status: {bug.status}\n"
                result += f"Severity: {bug.severity}\n"
                result += f"URL: {bug.page_url or 'N/A'}\n"
                result += f"Created: {bug.created_at}\n"
                result += f"\nDescription:\n{bug.description or 'No description'}\n"
                
                if bug.navigation_history:
                    result += f"\nNavigation History ({len(bug.navigation_history)} steps):\n"
                    for i, step in enumerate(bug.navigation_history[-10:], 1):
                        result += f"  {i}. {step.get('path', 'unknown')} ({step.get('action', 'unknown')})\n"
                
                if bug.screenshot_path:
                    result += f"\nScreenshot: {bug.screenshot_path}\n"
                
                if bug.comments:
                    result += f"\nComments ({len(bug.comments)}):\n"
                    for comment in bug.comments:
                        result += f"  [{comment.author}] {comment.content[:100]}...\n"
                
                return [TextContent(type="text", text=result)]

        elif name == "update_bug_status":
            bug_id = arguments.get("bug_id")
            status = arguments.get("status")
            
            with get_db() as db:
                bug = db.query(Bug).filter(Bug.id == bug_id).first()
                if not bug:
                    return [TextContent(type="text", text=f"Bug not found: {bug_id}")]
                
                old_status = bug.status
                bug.status = status
                db.commit()
                
                return [TextContent(
                    type="text",
                    text=f"Updated bug {bug_id}:\n  Status: {old_status} → {status}"
                )]

        elif name == "add_bug_comment":
            bug_id = arguments.get("bug_id")
            content = arguments.get("content")
            
            with get_db() as db:
                bug = db.query(Bug).filter(Bug.id == bug_id).first()
                if not bug:
                    return [TextContent(type="text", text=f"Bug not found: {bug_id}")]
                
                comment = BugComment(
                    bug_id=bug.id,
                    content=content,
                    author="ai",
                )
                db.add(comment)
                db.commit()
                
                return [TextContent(
                    type="text",
                    text=f"Added comment to bug {bug_id}:\n  {content[:100]}..."
                )]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        logger.error(f"Tool error: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# ============ SSE Transport ============

# Create SSE transport at module level
sse_transport = SseServerTransport("/messages")


@app.get("/sse")
async def sse_endpoint(request: Request):
    """SSE endpoint for MCP transport."""
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as (read_stream, write_stream):
        await mcp_server.run(
            read_stream, 
            write_stream, 
            mcp_server.create_initialization_options()
        )


@app.post("/messages")
async def messages_endpoint(request: Request):
    """Messages endpoint for MCP transport."""
    await sse_transport.handle_post_message(request.scope, request.receive, request._send)


# ============ Main Entry ============

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8082"))
    
    uvicorn.run(app, host=host, port=port)
