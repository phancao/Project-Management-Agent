#!/usr/bin/env python3
# Copyright (c) 2025 Galaxy Technology Service
# BugBase MCP Stdio Wrapper - Connects to BugBase API and exposes MCP tools via stdio

import asyncio
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# BugBase API URL (the REST API)
BUGBASE_API_URL = "http://localhost:8082"

# Create MCP server
mcp = Server("bugbase")


@mcp.list_tools()
async def list_tools():
    """List available MCP tools."""
    return [
        Tool(
            name="list_bugs",
            description="List all bug reports from BugBase with optional filters. Returns bugs sorted by creation date (newest first).",
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


@mcp.call_tool()
async def call_tool(name: str, arguments: dict):
    """Execute MCP tool by calling BugBase REST API."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if name == "list_bugs":
                params = {}
                if arguments.get("status"):
                    params["status"] = arguments["status"]
                if arguments.get("severity"):
                    params["severity"] = arguments["severity"]
                if arguments.get("limit"):
                    params["limit"] = arguments["limit"]
                
                response = await client.get(f"{BUGBASE_API_URL}/api/bugs", params=params)
                response.raise_for_status()
                data = response.json()
                
                bugs = data.get("bugs", [])
                result = f"Found {len(bugs)} bug(s):\n\n"
                for bug in bugs:
                    result += f"- [{bug['severity'].upper()}] {bug['title']}\n"
                    result += f"  ID: {bug['id']}\n"
                    result += f"  Status: {bug['status']}\n"
                    result += f"  URL: {bug.get('page_url', 'N/A')}\n"
                    result += f"  Created: {bug['created_at']}\n\n"
                
                return [TextContent(type="text", text=result)]

            elif name == "get_bug_details":
                bug_id = arguments.get("bug_id")
                response = await client.get(f"{BUGBASE_API_URL}/api/bugs/{bug_id}")
                response.raise_for_status()
                bug = response.json()
                
                result = f"Bug Details:\n"
                result += f"============\n"
                result += f"Title: {bug['title']}\n"
                result += f"ID: {bug['id']}\n"
                result += f"Status: {bug['status']}\n"
                result += f"Severity: {bug['severity']}\n"
                result += f"URL: {bug.get('page_url', 'N/A')}\n"
                result += f"Created: {bug['created_at']}\n"
                result += f"\nDescription:\n{bug.get('description') or 'No description'}\n"
                
                if bug.get('navigation_history'):
                    result += f"\nNavigation History ({len(bug['navigation_history'])} steps):\n"
                    for i, step in enumerate(bug['navigation_history'][-10:], 1):
                        result += f"  {i}. {step.get('path', 'unknown')} ({step.get('action', 'unknown')})\n"
                
                if bug.get('screenshot_path'):
                    result += f"\nScreenshot: {bug['screenshot_path']}\n"
                
                if bug.get('comments'):
                    result += f"\nComments ({len(bug['comments'])}):\n"
                    for comment in bug['comments']:
                        result += f"  [{comment['author']}] {comment['content'][:100]}...\n"
                
                return [TextContent(type="text", text=result)]

            elif name == "update_bug_status":
                bug_id = arguments.get("bug_id")
                status = arguments.get("status")
                
                response = await client.patch(
                    f"{BUGBASE_API_URL}/api/bugs/{bug_id}/status",
                    json={"status": status}
                )
                response.raise_for_status()
                
                return [TextContent(
                    type="text",
                    text=f"Updated bug {bug_id} status to: {status}"
                )]

            elif name == "add_bug_comment":
                bug_id = arguments.get("bug_id")
                content = arguments.get("content")
                
                response = await client.post(
                    f"{BUGBASE_API_URL}/api/bugs/{bug_id}/comments",
                    json={"content": content, "author": "ai"}
                )
                response.raise_for_status()
                
                return [TextContent(
                    type="text",
                    text=f"Added comment to bug {bug_id}: {content[:100]}..."
                )]

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except httpx.HTTPStatusError as e:
        return [TextContent(type="text", text=f"HTTP Error: {e.response.status_code} - {e.response.text}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the MCP server via stdio."""
    async with stdio_server() as (read_stream, write_stream):
        await mcp.run(read_stream, write_stream, mcp.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
