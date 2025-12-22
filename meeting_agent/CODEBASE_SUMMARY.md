# Meeting Agent - Codebase Summary

## Overview
AI agent that processes meeting recordings/transcripts to extract summaries, action items, decisions, and integrate with PM systems.

## Purpose
Listen to meetings → Transcribe → Summarize → Extract action items → Create PM tasks

---

## Module Structure

```
meeting_agent/
├── models/              # Data models
│   ├── meeting.py       # Meeting, Transcript, Participant
│   └── action_item.py   # ActionItem, Decision, FollowUp, MeetingSummary
├── audio/               # Audio processing
│   ├── processor.py     # AudioProcessor (ffmpeg)
│   └── transcriber.py   # Whisper API + local Whisper
├── analysis/            # LLM analysis
│   ├── summarizer.py    # MeetingSummarizer
│   └── action_extractor.py  # ActionExtractor
├── database/            # Persistence
│   ├── models.py        # SQLAlchemy ORM
│   └── repository.py    # CRUD operations
├── integrations/        # External systems
│   └── pm_integration.py  # PM task creation
├── handlers/            # Pipeline orchestration
│   └── meeting_handler.py  # Main handler
├── prompts/             # LLM prompts
│   ├── summarizer.md
│   └── action_extractor.md
└── config.py            # Configuration
```

---

## Key Components

### MeetingHandler
Main orchestrator - coordinates the full pipeline:
```
audio → validate → transcribe → summarize → extract → persist → create tasks
```

### Models
- `Meeting` - Core meeting entity with status, participants, transcript
- `Transcript` - Timestamped segments with speaker identification
- `ActionItem` - Extracted task with assignee, due date, priority
- `MeetingSummary` - Executive summary, key points, topics

### Audio Processing
- `AudioProcessor` - Validates, converts (ffmpeg), splits audio
- `Transcriber` - Whisper API or local whisper-1 model

### Analysis
- `MeetingSummarizer` - LLM-based summary generation
- `ActionExtractor` - LLM-based action/decision/follow-up extraction

### Database
- SQLite persistence via SQLAlchemy
- `MeetingRepository` - Full CRUD for all meeting data

---

## Usage

```python
from meeting_agent.handlers import MeetingHandler
from shared.handlers import HandlerContext

handler = MeetingHandler()
result = await handler.execute(
    HandlerContext(project_id="openproject:demo"),
    audio_path="meeting.mp3",
    meeting_title="Sprint Review",
    participants=["Alice", "Bob"],
)

if result.is_success:
    summary = result.data
    print(f"Action Items: {len(summary.action_items)}")
```

---

## Configuration

Environment variables:
- `OPENAI_API_KEY` - For Whisper API and LLM
- `MEETING_TRANSCRIPTION_PROVIDER` - whisper/whisper_local
- `MEETING_SUMMARY_MODEL` - gpt-4o-mini default
- `MEETING_AUTO_CREATE_TASKS` - Auto-create PM tasks

---

## Dependencies
- `shared/` - BaseHandler, HandlerResult
- `openai` - Whisper API, LLM
- `ffmpeg` - Audio processing (external)
- `sqlalchemy` - Database
