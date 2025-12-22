# Meeting Agent - AI Context

## When to Use This Module
- Processing meeting recordings (audio/video)
- Analyzing meeting transcripts
- Extracting action items, decisions, follow-ups
- Creating PM tasks from meetings

## Quick Reference

### Process a Meeting
```python
from meeting_agent.handlers import MeetingHandler
from shared.handlers import HandlerContext

handler = MeetingHandler()
result = await handler.execute(
    HandlerContext(project_id="openproject:demo"),
    audio_path="meeting.mp3",
    meeting_title="Sprint Review",
)
```

### Process Text Transcript
```python
result = await handler.process_from_text(
    context,
    transcript_text="Alice: We need to finish the API...",
    meeting_title="Quick Sync",
)
```

### Access Results
```python
summary = result.data  # MeetingSummary
summary.executive_summary  # str
summary.key_points  # List[str]
summary.action_items  # List[ActionItem]
summary.decisions  # List[Decision]
```

## Key Models

| Model | Key Fields |
|-------|------------|
| `Meeting` | id, title, status, participants, transcript, project_id |
| `ActionItem` | description, assignee_name, due_date, priority, pm_task_id |
| `Decision` | summary, decision_type, decision_makers |
| `MeetingSummary` | executive_summary, key_points, action_items, decisions |

## Status Flow
```
PENDING → TRANSCRIBING → ANALYZING → COMPLETED
                ↓                ↓
             FAILED          FAILED
```

## Don't Forget
- Requires `OPENAI_API_KEY` for transcription and analysis
- Audio needs ffmpeg installed for format conversion
- MeetingHandler auto-persists to SQLite database
- PM integration is optional (requires PM provider setup)

## Related Modules
- `shared/handlers/` - BaseHandler, HandlerResult
- `mcp_meeting_server/` - MCP tools for this agent
- `web/src/app/meeting/` - Frontend UI
