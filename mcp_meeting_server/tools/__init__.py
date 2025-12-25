"""
Meeting Processing Tools for MCP Server.

These tools expose meeting processing capabilities to AI agents.
"""

from typing import Any, Dict, List, Optional
import logging
import uuid
import uuid
import shutil
import os
import json
from pathlib import Path
from datetime import datetime

from mcp_server.database.models import (
    Meeting, Transcript, TranscriptSegment, 
    MeetingActionItem, MeetingParticipant, MeetingSummary,
    MeetingDecision
)

logger = logging.getLogger(__name__)

def register_meeting_tools(server, context, tool_names, tool_functions):
    """
    Register meeting tools with the PMMCPServer.
    
    Args:
        server: The MCP Server instance
        context: ToolContext instance
        tool_names: List to append tool names to
        tool_functions: Dict to register tool functions
    """
    
    # 1. Register tool definitions (schema) via list_tools handler
    # Note: PMMCPServer's _register_all_tools handles modules, 
    # but we need to ensure these tools are added to the tool_names list
    # so list_tools() returns them.
    
    tools_def = [
        {
            "name": "upload_meeting",
            "description": "Upload a meeting recording for processing. Returns meeting ID.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the audio/video file"},
                    "title": {"type": "string", "description": "Meeting title"},
                    "participants": {"type": "array", "items": {"type": "string"}, "description": "List of participant names"},
                    "project_id": {"type": "string", "description": "Optional PM project ID to link tasks to"}
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
                    "meeting_id": {"type": "string", "description": "Meeting ID from upload_meeting"},
                    "language": {"type": "string", "description": "Language code (e.g., 'en', 'vi') or null for auto-detect"}
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
                    "transcript": {"type": "string", "description": "The meeting transcript text"},
                    "title": {"type": "string", "description": "Meeting title"},
                    "participants": {"type": "array", "items": {"type": "string"}, "description": "List of participant names"},
                    "project_id": {"type": "string", "description": "Optional PM project ID"}
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
                    "meeting_id": {"type": "string", "description": "Meeting ID"}
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
                    "meeting_id": {"type": "string", "description": "Meeting ID"},
                    "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "all"], "description": "Filter by status"}
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
                    "meeting_id": {"type": "string", "description": "Meeting ID"},
                    "project_id": {"type": "string", "description": "PM project ID to create tasks in"},
                    "action_item_ids": {"type": "array", "items": {"type": "string"}, "description": "Specific action items to create"}
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
                    "status": {"type": "string", "enum": ["pending", "completed", "failed", "all"], "description": "Filter by processing status"},
                    "limit": {"type": "integer", "description": "Maximum number of meetings to return"},
                    "project_id": {"type": "string", "description": "Filter by project ID"}
                }
            }
        },
    ]

    # Add tool names
    for tool in tools_def:
        tool_names.append(tool["name"])
        
    # 2. Register tool functions (handlers)
    # We allow PMMCPServer.route_tool_call to dispatch to these functions.
    # We wrap them to inject 'context'.
    
    async def wrapped_handler(tool_func, name, args):
        return await tool_func(context, args)

    tool_functions["upload_meeting"] = lambda n, a: wrapped_handler(_handle_upload_meeting, n, a)
    tool_functions["process_meeting"] = lambda n, a: wrapped_handler(_handle_process_meeting, n, a)
    tool_functions["analyze_transcript"] = lambda n, a: wrapped_handler(_handle_analyze_transcript, n, a)
    tool_functions["get_meeting_summary"] = lambda n, a: wrapped_handler(_handle_get_summary, n, a)
    tool_functions["list_action_items"] = lambda n, a: wrapped_handler(_handle_list_action_items, n, a)
    tool_functions["create_tasks_from_meeting"] = lambda n, a: wrapped_handler(_handle_create_tasks, n, a)
    tool_functions["list_meetings"] = lambda n, a: wrapped_handler(_handle_list_meetings, n, a)

    return len(tools_def)


# --- Handlers ---

async def _handle_upload_meeting(context, args: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Handle upload_meeting tool"""
    file_path = args.get("file_path")
    title = args.get("title", "Untitled Meeting")
    participant_names = args.get("participants", [])
    project_id = args.get("project_id")
    
    # Generate meeting ID
    meeting_id = f"mtg_{uuid.uuid4().hex[:12]}"
    
    # Copy file to upload directory
    # Config is in env vars usually or we check env
    upload_dir = Path(os.getenv("MEETING_UPLOAD_DIR", "/app/uploads"))
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    src_path = Path(file_path)
    if not src_path.exists():
        # Fallback: maybe file_path IS the path in upload dir already?
        # If passed from API upload, it might be.
        # But if it's external, we need to copy.
        if (upload_dir / src_path.name).exists():
             src_path = upload_dir / src_path.name
        else:
             return [{"type": "text", "text": f"Error: File not found: {file_path}"}]
    
    dest_path = upload_dir / f"{meeting_id}{src_path.suffix}"
    if src_path != dest_path:
        shutil.copy2(src_path, dest_path)
    
    # Store meeting info in DB
    session = context.db
    # Note: context.db_session comes from caller, we don't close it here usually? 
    # PMMCPServer passes a session. We should use it.
    
    meeting = Meeting(
        id=meeting_id,
        title=title,
        file_path=str(dest_path),
        file_size_bytes=dest_path.stat().st_size,
        status="pending",
        project_id=project_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    session.add(meeting)
    
    # Add participants
    for name in participant_names:
        p = MeetingParticipant(
            meeting_id=meeting_id,
            name=name
        )
        session.add(p)
        
    session.commit()
    
    import json
    return [{
        "type": "text",
        "text": json.dumps({
            "meeting_id": meeting_id,
            "title": title,
            "message": "Meeting uploaded successfully. Use process_meeting to transcribe and analyze."
        })
    }]


async def _handle_process_meeting(context, args: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Handle process_meeting tool"""
    from shared.handlers import HandlerContext
    
    meeting_id = args.get("meeting_id")
    
    session = context.db
    meeting = session.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        return [{
            "type": "text",
            "text": json.dumps({
                "success": False,
                "error": f"Meeting not found: {meeting_id}"
            })
        }]
    
    meeting.status = "transcribing"
    meeting.updated_at = datetime.utcnow()
    session.commit()
    
    # Initialize MeetingHandler
    from meeting_agent.handlers import MeetingHandler
    from meeting_agent.config import MeetingAgentConfig
    from mcp_server.core.provider_manager import ProviderManager
    
    upload_dir = os.getenv("MEETING_UPLOAD_DIR", "/app/uploads")
    agent_config = MeetingAgentConfig(upload_dir=upload_dir)
    provider_mgr = ProviderManager(session)
    handler = MeetingHandler(config=agent_config, provider_manager=provider_mgr)
    
    # Get participants from DB
    participants = [p.name for p in meeting.participants]
    
    handler_context = HandlerContext(project_id=meeting.project_id)
    
    # NOTE: This call is blocking/long-running.
    result = await handler.execute(
        handler_context,
        audio_path=meeting.file_path,
        meeting_title=meeting.title,
        participants=participants,
        project_id=meeting.project_id,
    )
    
    if result.is_success:
        summary_data = result.data
        
        # Update meeting status
        meeting.status = "completed"
        meeting.processed_at = datetime.utcnow()
        meeting.updated_at = datetime.utcnow()
        
        # Save summary
        summary = MeetingSummary(
            meeting_id=meeting_id,
            content=summary_data.executive_summary,
            summary_type="executive"
        )
        session.add(summary)
        
        # Save action items
        for item in summary_data.action_items:
            ai = MeetingActionItem(
                meeting_id=meeting_id,
                description=item.description,
                status=item.status.value if hasattr(item.status, 'value') else str(item.status),
                assignee_name=item.assignee_name,
                due_date=item.due_date
            )
            session.add(ai)
        
        # Save decisions
        for decision_text in summary_data.decisions:
            dec = MeetingDecision(
                meeting_id=meeting_id,
                description=decision_text
            )
            session.add(dec)
            
        session.commit()
        
        return [{
            "type": "text",
            "text": json.dumps({
                "success": True,
                "message": "Meeting processed successfully",
                "summary": summary_data.executive_summary,
                "action_items_count": len(summary_data.action_items),
                "decisions_count": len(summary_data.decisions)
            })
        }]
    else:
        meeting.status = "failed"
        meeting.error_message = result.message
        meeting.updated_at = datetime.utcnow()
        session.commit()
        return [{
            "type": "text",
            "text": json.dumps({
                "success": False,
                "error": result.message
            })
        }]


async def _handle_analyze_transcript(context, args: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Handle analyze_transcript tool"""
    from shared.handlers import HandlerContext
    
    transcript_text = args.get("transcript")
    title = args.get("title", "Meeting from Transcript")
    participant_names = args.get("participants", [])
    project_id = args.get("project_id")
    
    # Create meeting record
    meeting_id = f"mtg_{uuid.uuid4().hex[:12]}"
    
    session = context.db
    meeting = Meeting(
        id=meeting_id,
        title=title,
        status="analyzing",
        project_id=project_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    session.add(meeting)
    
    # Add participants
    for name in participant_names:
        p = MeetingParticipant(
            meeting_id=meeting_id,
            name=name
        )
        session.add(p)
        
    # Add transcript
    transcript_record = Transcript(
        meeting_id=meeting_id,
        full_text=transcript_text,
        word_count=len(transcript_text.split())
    )
    session.add(transcript_record)
    session.commit()
    
    # Process
    from meeting_agent.handlers import MeetingHandler
    from meeting_agent.config import MeetingAgentConfig
    from mcp_server.core.provider_manager import ProviderManager
    
    upload_dir = os.getenv("MEETING_UPLOAD_DIR", "/app/uploads")
    agent_config = MeetingAgentConfig(upload_dir=upload_dir)
    provider_mgr = ProviderManager(session)
    handler = MeetingHandler(config=agent_config, provider_manager=provider_mgr)

    handler_context = HandlerContext(project_id=project_id)
    
    result = await handler.process_from_text(
        handler_context,
        transcript_text=transcript_text,
        meeting_title=title,
        participants=participant_names,
        project_id=project_id,
    )
    
    if result.is_success:
        summary_data = result.data
        
        meeting.status = "completed"
        meeting.processed_at = datetime.utcnow()
        
        # Save summary
        summary = MeetingSummary(
            meeting_id=meeting_id,
            content=summary_data.executive_summary,
            summary_type="executive"
        )
        session.add(summary)
        
        # Save action items
        for item in summary_data.action_items:
            ai = MeetingActionItem(
                meeting_id=meeting_id,
                description=item.description,
                status=item.status.value if hasattr(item.status, 'value') else str(item.status),
                assignee_name=item.assignee_name,
                due_date=item.due_date
            )
            session.add(ai)
        
        # Save decisions
        for decision_text in summary_data.decisions:
            dec = MeetingDecision(
                meeting_id=meeting_id,
                description=decision_text
            )
            session.add(dec)
            
        session.commit()
        
        return [{
            "type": "text",
            "text": f"""Transcript analyzed!

**Summary:** {summary_data.executive_summary}

**Action Items:** {len(summary_data.action_items)}
**Decisions:** {len(summary_data.decisions)}"""
        }]
    else:
        meeting.status = "failed"
        meeting.error_message = result.message
        session.commit()
        return [{"type": "text", "text": f"Error: {result.message}"}]


async def _handle_get_summary(context, args: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Handle get_meeting_summary tool"""
    meeting_id = args.get("meeting_id")
    
    session = context.db
    meeting = session.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        return [{"type": "text", "text": f"No meeting found: {meeting_id}"}]
    
    summary = session.query(MeetingSummary).filter(MeetingSummary.meeting_id == meeting_id).first()
    
    if not summary:
            return [{"type": "text", "text": f"No summary available for meeting: {meeting_id} (Status: {meeting.status})"}]
    
    return [{
        "type": "text",
        "text": summary.content
    }]


async def _handle_list_action_items(context, args: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Handle list_action_items tool"""
    meeting_id = args.get("meeting_id")
    status_filter = args.get("status", "all")
    
    session = context.db
    query = session.query(MeetingActionItem).filter(MeetingActionItem.meeting_id == meeting_id)
    
    if status_filter != "all":
        query = query.filter(MeetingActionItem.status == status_filter)
        
    items = query.all()
    
    if not items:
        return [{"type": "text", "text": "No action items found."}]
    
    lines = [f"# Action Items ({len(items)})"]
    for item in items:
        assignee = f" (@{item.assignee_name})" if item.assignee_name else ""
        due = f" - Due: {item.due_date}" if item.due_date else ""
        lines.append(f"- [{item.status}] {item.description}{assignee}{due}")
    
    return [{"type": "text", "text": "\\n".join(lines)}]


async def _handle_create_tasks(context, args: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Handle create_tasks_from_meeting tool"""
    meeting_id = args.get("meeting_id")
    project_id = args.get("project_id")
    action_item_ids = args.get("action_item_ids", [])
    
    session = context.db
    query = session.query(MeetingActionItem).filter(MeetingActionItem.meeting_id == meeting_id)
    
    if action_item_ids:
        # We would filter by IDs here
        pass
        
    items = query.all()
    
    if not items:
            return [{"type": "text", "text": "No action items to convert."}]

    # Mock creating tasks
    created_count = 0
    for item in items:
            task_id = f"task_{uuid.uuid4().hex[:8]}"
            item.pm_task_id = task_id
            created_count += 1
    
    session.commit()

    return [{
        "type": "text",
        "text": f"Created {created_count} tasks in project {project_id}.\\n(Note: Task creation is currently mocked, but DB is updated)"
    }]


async def _handle_list_meetings(context, args: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Handle list_meetings tool"""
    status_filter = args.get("status", "all")
    limit = args.get("limit", 20)
    project_id = args.get("project_id")
    
    session = context.db
    query = session.query(Meeting).order_by(Meeting.created_at.desc())
    
    if status_filter != "all":
        query = query.filter(Meeting.status == status_filter)

    if project_id:
        query = query.filter(Meeting.project_id == project_id)
        
    meetings = query.limit(limit).all()
    
    # Return JSON structure for API, or text for LLM?
    # For HTTP API bridging, return dict is better? 
    # But tools must return List[Content].
    # WE need to return standard tool response.
    # BRIDGE in sse.py extracts result.
    
    if not meetings:
        return [{"type": "text", "text": "No meetings found."}]
        
    # Construct a rich response that can be parsed as JSON by the API bridge
    # but still readable as text by LLM.
    
    import json
    
    meeting_list = []
    for m in meetings:
        meeting_list.append({
            "id": m.id,
            "title": m.title,
            "status": m.status,
            "createdAt": m.created_at.isoformat() if m.created_at else None,
            "projectId": m.project_id,
            "participantsCount": len(m.participants) if m.participants else 0,
            "actionItemsCount": len(m.action_items) if m.action_items else 0
        })
    
    # Return JSON string in text
    return [{"type": "text", "text": json.dumps({"meetings": meeting_list})}]
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
    
