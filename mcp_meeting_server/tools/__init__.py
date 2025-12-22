"""
Meeting Processing Tools for MCP Server.

These tools expose meeting processing capabilities to AI agents.
"""

from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


def register_all_tools(server, mcp_server):
    """
    Register all meeting tools with the MCP server.
    
    Args:
        server: The MCP Server instance
        mcp_server: The MeetingMCPServer instance for accessing services
    """
    
    @server.list_tools()
    async def list_tools() -> List[Dict[str, Any]]:
        """List all available meeting tools"""
        return [
            {
                "name": "upload_meeting",
                "description": "Upload a meeting recording for processing. Returns meeting ID.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the audio/video file"
                        },
                        "title": {
                            "type": "string",
                            "description": "Meeting title"
                        },
                        "participants": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of participant names"
                        },
                        "project_id": {
                            "type": "string",
                            "description": "Optional PM project ID to link tasks to"
                        }
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "process_meeting",
                "description": "Process an uploaded meeting: transcribe, summarize, and extract action items.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "meeting_id": {
                            "type": "string",
                            "description": "Meeting ID from upload_meeting"
                        },
                        "language": {
                            "type": "string",
                            "description": "Language code (e.g., 'en', 'vi') or null for auto-detect"
                        }
                    },
                    "required": ["meeting_id"]
                }
            },
            {
                "name": "analyze_transcript",
                "description": "Analyze a text transcript directly without audio processing.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "transcript": {
                            "type": "string",
                            "description": "The meeting transcript text"
                        },
                        "title": {
                            "type": "string",
                            "description": "Meeting title"
                        },
                        "participants": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of participant names"
                        },
                        "project_id": {
                            "type": "string",
                            "description": "Optional PM project ID"
                        }
                    },
                    "required": ["transcript"]
                }
            },
            {
                "name": "get_meeting_summary",
                "description": "Get the summary and analysis results for a processed meeting.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "meeting_id": {
                            "type": "string",
                            "description": "Meeting ID"
                        }
                    },
                    "required": ["meeting_id"]
                }
            },
            {
                "name": "list_action_items",
                "description": "List action items extracted from a meeting.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "meeting_id": {
                            "type": "string",
                            "description": "Meeting ID"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed", "all"],
                            "description": "Filter by status"
                        }
                    },
                    "required": ["meeting_id"]
                }
            },
            {
                "name": "create_tasks_from_meeting",
                "description": "Create PM tasks from meeting action items.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "meeting_id": {
                            "type": "string",
                            "description": "Meeting ID"
                        },
                        "project_id": {
                            "type": "string",
                            "description": "PM project ID to create tasks in"
                        },
                        "action_item_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific action items to create, or empty for all"
                        }
                    },
                    "required": ["meeting_id", "project_id"]
                }
            },
            {
                "name": "list_meetings",
                "description": "List all processed meetings.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["pending", "completed", "failed", "all"],
                            "description": "Filter by processing status"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of meetings to return"
                        }
                    }
                }
            },
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle tool calls"""
        try:
            if name == "upload_meeting":
                return await _handle_upload_meeting(mcp_server, arguments)
            elif name == "process_meeting":
                return await _handle_process_meeting(mcp_server, arguments)
            elif name == "analyze_transcript":
                return await _handle_analyze_transcript(mcp_server, arguments)
            elif name == "get_meeting_summary":
                return await _handle_get_summary(mcp_server, arguments)
            elif name == "list_action_items":
                return await _handle_list_action_items(mcp_server, arguments)
            elif name == "create_tasks_from_meeting":
                return await _handle_create_tasks(mcp_server, arguments)
            elif name == "list_meetings":
                return await _handle_list_meetings(mcp_server, arguments)
            else:
                return [{"type": "text", "text": f"Unknown tool: {name}"}]
                
        except Exception as e:
            logger.exception(f"Tool {name} failed: {e}")
            return [{"type": "text", "text": f"Error: {str(e)}"}]


# In-memory storage for demo (replace with database in production)
_meetings_store: Dict[str, Any] = {}
_summaries_store: Dict[str, Any] = {}


async def _handle_upload_meeting(mcp_server, args: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Handle upload_meeting tool"""
    import uuid
    import shutil
    from pathlib import Path
    
    file_path = args.get("file_path")
    title = args.get("title", "Untitled Meeting")
    participants = args.get("participants", [])
    project_id = args.get("project_id")
    
    # Generate meeting ID
    meeting_id = f"mtg_{uuid.uuid4().hex[:12]}"
    
    # Copy file to upload directory
    upload_dir = mcp_server.get_upload_dir()
    src_path = Path(file_path)
    
    if not src_path.exists():
        return [{"type": "text", "text": f"Error: File not found: {file_path}"}]
    
    dest_path = upload_dir / f"{meeting_id}{src_path.suffix}"
    shutil.copy2(src_path, dest_path)
    
    # Store meeting info
    _meetings_store[meeting_id] = {
        "id": meeting_id,
        "title": title,
        "participants": participants,
        "project_id": project_id,
        "file_path": str(dest_path),
        "status": "pending",
    }
    
    return [{
        "type": "text",
        "text": f"Meeting uploaded successfully.\nMeeting ID: {meeting_id}\nTitle: {title}\nParticipants: {', '.join(participants) or 'None specified'}\nUse process_meeting to transcribe and analyze."
    }]


async def _handle_process_meeting(mcp_server, args: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Handle process_meeting tool"""
    from shared.handlers import HandlerContext
    
    meeting_id = args.get("meeting_id")
    language = args.get("language")
    
    if meeting_id not in _meetings_store:
        return [{"type": "text", "text": f"Error: Meeting not found: {meeting_id}"}]
    
    meeting_info = _meetings_store[meeting_id]
    
    # Get handler and process
    handler = mcp_server.get_meeting_handler()
    context = HandlerContext(project_id=meeting_info.get("project_id"))
    
    result = await handler.execute(
        context,
        audio_path=meeting_info["file_path"],
        meeting_title=meeting_info["title"],
        participants=meeting_info["participants"],
        project_id=meeting_info.get("project_id"),
    )
    
    if result.is_success:
        summary = result.data
        _summaries_store[meeting_id] = summary
        _meetings_store[meeting_id]["status"] = "completed"
        
        return [{
            "type": "text",
            "text": f"""Meeting processed successfully!

**Summary:** {summary.executive_summary}

**Key Points:**
{chr(10).join(f'- {p}' for p in summary.key_points[:5])}

**Action Items:** {len(summary.action_items)}
**Decisions:** {len(summary.decisions)}
**Follow-ups:** {len(summary.follow_ups)}

Use get_meeting_summary or list_action_items for more details."""
        }]
    else:
        _meetings_store[meeting_id]["status"] = "failed"
        return [{"type": "text", "text": f"Error processing meeting: {result.message}"}]


async def _handle_analyze_transcript(mcp_server, args: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Handle analyze_transcript tool"""
    from shared.handlers import HandlerContext
    
    transcript = args.get("transcript")
    title = args.get("title", "Meeting from Transcript")
    participants = args.get("participants", [])
    project_id = args.get("project_id")
    
    handler = mcp_server.get_meeting_handler()
    context = HandlerContext(project_id=project_id)
    
    result = await handler.process_from_text(
        context,
        transcript_text=transcript,
        meeting_title=title,
        participants=participants,
        project_id=project_id,
    )
    
    if result.is_success:
        summary = result.data
        meeting_id = result.metadata.get("meeting_id", "temp")
        _summaries_store[meeting_id] = summary
        
        return [{
            "type": "text",
            "text": f"""Transcript analyzed!

**Summary:** {summary.executive_summary}

**Action Items:** {len(summary.action_items)}
{chr(10).join(f'- {ai.description}' for ai in summary.action_items[:5])}

**Decisions:** {len(summary.decisions)}"""
        }]
    else:
        return [{"type": "text", "text": f"Error: {result.message}"}]


async def _handle_get_summary(mcp_server, args: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Handle get_meeting_summary tool"""
    meeting_id = args.get("meeting_id")
    
    if meeting_id not in _summaries_store:
        return [{"type": "text", "text": f"No summary found for meeting: {meeting_id}"}]
    
    summary = _summaries_store[meeting_id]
    
    return [{
        "type": "text",
        "text": summary.to_markdown() if hasattr(summary, 'to_markdown') else str(summary)
    }]


async def _handle_list_action_items(mcp_server, args: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Handle list_action_items tool"""
    meeting_id = args.get("meeting_id")
    status_filter = args.get("status", "all")
    
    if meeting_id not in _summaries_store:
        return [{"type": "text", "text": f"No data found for meeting: {meeting_id}"}]
    
    summary = _summaries_store[meeting_id]
    items = summary.action_items
    
    if status_filter != "all":
        items = [i for i in items if i.status.value == status_filter]
    
    if not items:
        return [{"type": "text", "text": "No action items found."}]
    
    lines = [f"# Action Items ({len(items)})"]
    for item in items:
        assignee = f" (@{item.assignee_name})" if item.assignee_name else ""
        due = f" - Due: {item.due_date}" if item.due_date else ""
        lines.append(f"- [{item.status.value}] {item.description}{assignee}{due}")
    
    return [{"type": "text", "text": "\n".join(lines)}]


async def _handle_create_tasks(mcp_server, args: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Handle create_tasks_from_meeting tool"""
    meeting_id = args.get("meeting_id")
    project_id = args.get("project_id")
    action_item_ids = args.get("action_item_ids", [])
    
    if meeting_id not in _summaries_store:
        return [{"type": "text", "text": f"No data found for meeting: {meeting_id}"}]
    
    summary = _summaries_store[meeting_id]
    items = summary.action_items
    
    if action_item_ids:
        items = [i for i in items if i.id in action_item_ids]
    
    # Note: In production, this would call the PM handler to create tasks
    return [{
        "type": "text",
        "text": f"Would create {len(items)} tasks in project {project_id}.\n\nNote: PM integration pending. Action items:\n" + 
                "\n".join(f"- {i.description}" for i in items)
    }]


async def _handle_list_meetings(mcp_server, args: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Handle list_meetings tool"""
    status_filter = args.get("status", "all")
    limit = args.get("limit", 20)
    
    meetings = list(_meetings_store.values())
    
    if status_filter != "all":
        meetings = [m for m in meetings if m["status"] == status_filter]
    
    meetings = meetings[:limit]
    
    if not meetings:
        return [{"type": "text", "text": "No meetings found."}]
    
    lines = [f"# Meetings ({len(meetings)})"]
    for m in meetings:
        lines.append(f"- [{m['status']}] {m['id']}: {m['title']}")
    
    return [{"type": "text", "text": "\n".join(lines)}]
