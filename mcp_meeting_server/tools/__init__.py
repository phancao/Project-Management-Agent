"""
Meeting Processing Tools for MCP Server.

These tools expose meeting processing capabilities to AI agents.
"""

from typing import Any, Dict, List, Optional
import logging
import uuid
import shutil
from pathlib import Path
from datetime import datetime

from database.orm_models import (
    Meeting, Transcript, TranscriptSegment, 
    MeetingActionItem, MeetingParticipant, MeetingSummary,
    MeetingDecision
)

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


async def _handle_upload_meeting(mcp_server, args: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Handle upload_meeting tool"""
    file_path = args.get("file_path")
    title = args.get("title", "Untitled Meeting")
    participant_names = args.get("participants", [])
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
    
    # Store meeting info in DB
    session = mcp_server.get_db_session()
    try:
        meeting = Meeting(
            id=meeting_id,
            title=title,
            file_path=str(dest_path),
            file_size_bytes=src_path.stat().st_size,
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
    finally:
        session.close()
    
    return [{
        "type": "text",
        "text": f"Meeting uploaded successfully.\nMeeting ID: {meeting_id}\nTitle: {title}\nParticipants: {', '.join(participant_names) or 'None specified'}\nUse process_meeting to transcribe and analyze."
    }]


async def _handle_process_meeting(mcp_server, args: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Handle process_meeting tool"""
    from shared.handlers import HandlerContext
    
    meeting_id = args.get("meeting_id")
    
    session = mcp_server.get_db_session()
    try:
        meeting = session.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            return [{"type": "text", "text": f"Error: Meeting not found: {meeting_id}"}]
        
        meeting.status = "transcribing"
        meeting.updated_at = datetime.utcnow()
        session.commit()
        
        # Get handler and process
        handler = mcp_server.get_meeting_handler()
        
        # Get participants from DB
        participants = [p.name for p in meeting.participants]
        
        context = HandlerContext(project_id=meeting.project_id)
        
        # NOTE: This call is blocking/long-running. In production, consider background task.
        result = await handler.execute(
            context,
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
                "text": f"""Meeting processed successfully!

**Summary:** {summary_data.executive_summary}

**Action Items:** {len(summary_data.action_items)}
**Decisions:** {len(summary_data.decisions)}

Use get_meeting_summary or list_action_items for more details."""
            }]
        else:
            meeting.status = "failed"
            meeting.error_message = result.message
            meeting.updated_at = datetime.utcnow()
            session.commit()
            return [{"type": "text", "text": f"Error processing meeting: {result.message}"}]
            
    finally:
        session.close()


async def _handle_analyze_transcript(mcp_server, args: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Handle analyze_transcript tool"""
    from shared.handlers import HandlerContext
    
    transcript_text = args.get("transcript")
    title = args.get("title", "Meeting from Transcript")
    participant_names = args.get("participants", [])
    project_id = args.get("project_id")
    
    # Create meeting record
    meeting_id = f"mtg_{uuid.uuid4().hex[:12]}"
    
    session = mcp_server.get_db_session()
    try:
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
        handler = mcp_server.get_meeting_handler()
        context = HandlerContext(project_id=project_id)
        
        result = await handler.process_from_text(
            context,
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
            
    finally:
        session.close()


async def _handle_get_summary(mcp_server, args: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Handle get_meeting_summary tool"""
    meeting_id = args.get("meeting_id")
    
    session = mcp_server.get_db_session()
    try:
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
    finally:
        session.close()


async def _handle_list_action_items(mcp_server, args: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Handle list_action_items tool"""
    meeting_id = args.get("meeting_id")
    status_filter = args.get("status", "all")
    
    session = mcp_server.get_db_session()
    try:
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
        
        return [{"type": "text", "text": "\n".join(lines)}]
    finally:
        session.close()


async def _handle_create_tasks(mcp_server, args: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Handle create_tasks_from_meeting tool"""
    meeting_id = args.get("meeting_id")
    project_id = args.get("project_id")
    action_item_ids = args.get("action_item_ids", [])
    
    # Note: In production, this would call the PM service to create tasks
    # For now, we update the DB to reflect we "created" them
    
    session = mcp_server.get_db_session()
    try:
        query = session.query(MeetingActionItem).filter(MeetingActionItem.meeting_id == meeting_id)
        
        if action_item_ids:
            # We would filter by IDs here, but since input IDs might be different from DB IDs 
            # (if we exposed UUIDs to user), we need to handle that.
            # For this MVP, we ignore individual selection to avoid ID complexity
            pass
            
        items = query.all()
        
        if not items:
             return [{"type": "text", "text": "No action items to convert."}]

        # Mock creating tasks
        created_count = 0
        for item in items:
             task_id = f"task_{uuid.uuid4().hex[:8]}"
             item.pm_task_id = task_id
             # item.status = "in_progress" # Maybe?
             created_count += 1
        
        session.commit()

        return [{
            "type": "text",
            "text": f"Created {created_count} tasks in project {project_id}.\n(Note: Task creation is currently mocked, but DB is updated)"
        }]
    finally:
        session.close()


async def _handle_list_meetings(mcp_server, args: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Handle list_meetings tool"""
    status_filter = args.get("status", "all")
    limit = args.get("limit", 20)
    
    session = mcp_server.get_db_session()
    try:
        query = session.query(Meeting).order_by(Meeting.created_at.desc())
        
        if status_filter != "all":
            query = query.filter(Meeting.status == status_filter)
            
        meetings = query.limit(limit).all()
        
        if not meetings:
            return [{"type": "text", "text": "No meetings found."}]
        
        lines = [f"# Meetings ({len(meetings)})"]
        for m in meetings:
            lines.append(f"- [{m.status}] {m.id}: {m.title}")
        
        return [{"type": "text", "text": "\n".join(lines)}]
    finally:
        session.close()
