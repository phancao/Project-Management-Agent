"""
Integration tests for Meeting Agent.

Tests the full processing pipeline with mocked external services.
"""

import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from meeting_agent.handlers import MeetingHandler
from meeting_agent.config import MeetingAgentConfig, TranscriptionProvider
from meeting_agent.models import (
    Meeting,
    MeetingStatus,
    Transcript,
    TranscriptSegment,
    ActionItem,
    ActionItemPriority,
    MeetingSummary,
)
from meeting_agent.database import MeetingRepository
from shared.handlers import HandlerContext


class TestMeetingHandlerIntegration:
    """Integration tests for the meeting handler pipeline"""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database"""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test_meetings.db")
        yield f"sqlite:///{db_path}"
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def handler(self, temp_db):
        """Create a meeting handler with temp database"""
        config = MeetingAgentConfig(
            transcription_provider=TranscriptionProvider.WHISPER,
            upload_dir=tempfile.mkdtemp(),
        )
        return MeetingHandler(config=config, database_url=temp_db)

    @pytest.fixture
    def mock_transcription_result(self):
        """Create a mock transcription result"""
        from meeting_agent.audio import TranscriptionResult
        
        transcript = Transcript(
            meeting_id="test",
            language="en",
            segments=[
                TranscriptSegment(
                    id="seg_1",
                    speaker="Alice",
                    text="Let's discuss the new feature.",
                    start_time=0.0,
                    end_time=3.0,
                ),
                TranscriptSegment(
                    id="seg_2",
                    speaker="Bob",
                    text="I'll work on the API integration by Friday.",
                    start_time=3.5,
                    end_time=7.0,
                ),
            ],
            full_text="Let's discuss the new feature. I'll work on the API integration by Friday.",
            word_count=13,
            duration_seconds=7.0,
        )
        
        return TranscriptionResult(
            success=True,
            transcript=transcript,
            language="en",
            duration_seconds=7.0,
        )

    @pytest.mark.asyncio
    async def test_full_processing_pipeline(self, handler, mock_transcription_result):
        """Test the complete meeting processing pipeline"""
        # Create a temp audio file
        temp_audio = os.path.join(handler.config.upload_dir, "test.mp3")
        Path(temp_audio).write_bytes(b"fake audio content")
        
        # Mock the transcriber
        handler.transcriber.transcribe = AsyncMock(return_value=mock_transcription_result)
        
        # Mock the summarizer
        mock_summary = MeetingSummary(
            meeting_id="test",
            executive_summary="Team discussed new feature and API integration.",
            key_points=["New feature discussion", "API integration by Friday"],
            topics=["Features", "API"],
        )
        handler.summarizer.summarize = AsyncMock(return_value=mock_summary)
        
        # Mock the action extractor
        mock_actions = [
            ActionItem(
                id="ai_1",
                meeting_id="test",
                description="Complete API integration",
                assignee_name="Bob",
                priority=ActionItemPriority.HIGH,
            )
        ]
        handler.action_extractor.extract = AsyncMock(return_value=(mock_actions, [], []))
        
        # Execute
        context = HandlerContext(user_id="test_user")
        result = await handler.execute(
            context,
            audio_path=temp_audio,
            meeting_title="Test Meeting",
            participants=["Alice", "Bob"],
        )
        
        # Verify
        assert result.is_success
        assert result.data is not None
        assert result.data.executive_summary == "Team discussed new feature and API integration."
        assert len(result.data.action_items) == 1
        assert result.data.action_items[0].assignee_name == "Bob"
        
        # Verify transcriber was called
        handler.transcriber.transcribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_from_text(self, handler):
        """Test processing from raw transcript text"""
        transcript = """
        Alice: Welcome everyone to the sprint planning.
        Bob: I think we should prioritize the login feature.
        Charlie: Agreed. I can work on the UI by Wednesday.
        Alice: Great. Charlie, please create the wireframes first.
        """
        
        # Mock the summarizer
        mock_summary = MeetingSummary(
            meeting_id="test",
            executive_summary="Sprint planning meeting to prioritize features.",
            key_points=["Login feature prioritized", "UI work by Wednesday"],
        )
        handler.summarizer.summarize = AsyncMock(return_value=mock_summary)
        
        # Mock the action extractor
        mock_actions = [
            ActionItem(
                id="ai_1",
                meeting_id="test",
                description="Create wireframes for login UI",
                assignee_name="Charlie",
                priority=ActionItemPriority.MEDIUM,
            )
        ]
        handler.action_extractor.extract = AsyncMock(return_value=(mock_actions, [], []))
        
        # Execute
        context = HandlerContext()
        result = await handler.process_from_text(
            context,
            transcript_text=transcript,
            meeting_title="Sprint Planning",
            participants=["Alice", "Bob", "Charlie"],
        )
        
        # Verify
        assert result.is_success
        assert "Sprint planning" in result.data.executive_summary


class TestDatabaseIntegration:
    """Integration tests for database operations"""

    @pytest.fixture
    def repository(self):
        """Create a repository with an in-memory database"""
        return MeetingRepository("sqlite:///:memory:")

    def test_meeting_crud_cycle(self, repository):
        """Test complete CRUD cycle for meetings"""
        from meeting_agent.models import Participant
        
        # Create
        meeting = Meeting(
            id="mtg_test123",
            title="Test Meeting",
            participants=[
                Participant(name="Alice"),
                Participant(name="Bob"),
            ],
        )
        created = repository.create_meeting(meeting)
        
        # Read
        fetched = repository.get_meeting("mtg_test123")
        assert fetched is not None
        assert fetched.title == "Test Meeting"
        assert len(fetched.participants) == 2
        
        # Update status
        repository.update_meeting_status("mtg_test123", MeetingStatus.COMPLETED)
        updated = repository.get_meeting("mtg_test123")
        assert updated.status == MeetingStatus.COMPLETED
        
        # List
        meetings = repository.list_meetings()
        assert len(meetings) == 1
        
        # Delete
        deleted = repository.delete_meeting("mtg_test123")
        assert deleted is True
        assert repository.get_meeting("mtg_test123") is None

    def test_action_items_persistence(self, repository):
        """Test saving and retrieving action items"""
        from meeting_agent.models import Participant
        from datetime import date
        
        # Create meeting first
        meeting = Meeting(id="mtg_ai_test", title="Action Item Test")
        repository.create_meeting(meeting)
        
        # Save action items
        action_items = [
            ActionItem(
                id="ai_001",
                meeting_id="mtg_ai_test",
                description="Complete the report",
                assignee_name="Alice",
                priority=ActionItemPriority.HIGH,
                due_date=date(2024, 1, 15),
            ),
            ActionItem(
                id="ai_002",
                meeting_id="mtg_ai_test",
                description="Review PR",
                assignee_name="Bob",
                priority=ActionItemPriority.MEDIUM,
            ),
        ]
        repository.save_action_items("mtg_ai_test", action_items)
        
        # Retrieve
        retrieved = repository.get_action_items("mtg_ai_test")
        assert len(retrieved) == 2
        assert retrieved[0].description == "Complete the report"
        assert retrieved[0].priority == ActionItemPriority.HIGH

    def test_summary_persistence(self, repository):
        """Test saving and retrieving meeting summaries"""
        # Create meeting first
        meeting = Meeting(id="mtg_sum_test", title="Summary Test")
        repository.create_meeting(meeting)
        
        # Save summary
        summary = MeetingSummary(
            meeting_id="mtg_sum_test",
            executive_summary="A productive meeting about project planning.",
            key_points=["Point 1", "Point 2", "Point 3"],
            topics=["Planning", "Resources"],
        )
        repository.save_summary("mtg_sum_test", summary)
        
        # Retrieve
        retrieved = repository.get_summary("mtg_sum_test")
        assert retrieved is not None
        assert "productive meeting" in retrieved.executive_summary
        assert len(retrieved.key_points) == 3


class TestPMIntegration:
    """Integration tests for PM provider connection"""

    @pytest.mark.asyncio
    async def test_task_creation_without_pm_service(self):
        """Test graceful handling when PM service is unavailable"""
        from meeting_agent.integrations import MeetingPMIntegration
        
        integration = MeetingPMIntegration(pm_service=None)
        
        action_item = ActionItem(
            id="ai_test",
            meeting_id="mtg_test",
            description="Test action item",
        )
        
        result = await integration.create_task_from_action_item(
            action_item,
            project_id="test:project",
        )
        
        # Should fail gracefully
        assert result.is_failed
        assert "not available" in result.message.lower()
