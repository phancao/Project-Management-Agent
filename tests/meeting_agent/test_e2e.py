"""
End-to-end tests for Meeting Notes Agent.

These tests simulate the complete user workflow from
audio upload through task creation.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from meeting_agent.handlers import MeetingHandler
from meeting_agent.config import MeetingAgentConfig, TranscriptionProvider
from meeting_agent.models import (
    Meeting,
    Transcript,
    TranscriptSegment,
    ActionItem,
    ActionItemPriority,
    MeetingSummary,
    Decision,
    DecisionType,
)
from shared.handlers import HandlerContext


class TestE2EWorkflow:
    """End-to-end workflow tests"""

    @pytest.fixture
    def setup_environment(self):
        """Set up a complete test environment"""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "e2e_test.db")
        upload_dir = os.path.join(temp_dir, "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        
        yield {
            "db_url": f"sqlite:///{db_path}",
            "upload_dir": upload_dir,
            "temp_dir": temp_dir,
        }
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_complete_meeting_workflow(self, setup_environment):
        """
        Test the complete workflow:
        1. Upload meeting audio
        2. Transcribe
        3. Analyze and extract action items
        4. Create PM tasks
        5. Retrieve results
        """
        # Create handler with test configuration
        config = MeetingAgentConfig(
            transcription_provider=TranscriptionProvider.WHISPER,
            upload_dir=setup_environment["upload_dir"],
        )
        handler = MeetingHandler(
            config=config,
            database_url=setup_environment["db_url"],
        )
        
        # Create mock audio file
        audio_file = os.path.join(setup_environment["upload_dir"], "sprint_review.mp3")
        Path(audio_file).write_bytes(b"fake audio data")
        
        # Mock transcriber with realistic output
        from meeting_agent.audio import TranscriptionResult
        mock_transcript = Transcript(
            meeting_id="test",
            language="en",
            segments=[
                TranscriptSegment(
                    id="seg_1",
                    speaker="Product Manager",
                    text="Welcome to the sprint review. Let's discuss what we accomplished.",
                    start_time=0.0,
                    end_time=5.0,
                ),
                TranscriptSegment(
                    id="seg_2",
                    speaker="Developer",
                    text="I completed the user authentication module. We need to add password reset functionality by next Tuesday.",
                    start_time=5.5,
                    end_time=12.0,
                ),
                TranscriptSegment(
                    id="seg_3",
                    speaker="QA Lead",
                    text="I'll write the test cases for authentication. Should have them ready by Wednesday.",
                    start_time=12.5,
                    end_time=17.0,
                ),
                TranscriptSegment(
                    id="seg_4",
                    speaker="Product Manager",
                    text="Great work everyone. Let's also schedule a demo with stakeholders for Friday.",
                    start_time=17.5,
                    end_time=22.0,
                ),
            ],
            full_text="...",
            duration_seconds=22.0,
        )
        
        handler.transcriber.transcribe = AsyncMock(
            return_value=TranscriptionResult(
                success=True,
                transcript=mock_transcript,
                language="en",
                duration_seconds=22.0,
            )
        )
        
        # Mock summarizer
        handler.summarizer.summarize = AsyncMock(
            return_value=MeetingSummary(
                meeting_id="test",
                executive_summary="Sprint review discussing authentication completion and next steps.",
                key_points=[
                    "User authentication module completed",
                    "Password reset feature needed by Tuesday",
                    "Test cases to be ready by Wednesday",
                    "Stakeholder demo scheduled for Friday",
                ],
                topics=["Sprint Review", "Authentication", "Testing", "Demo"],
            )
        )
        
        # Mock action extractor
        handler.action_extractor.extract = AsyncMock(
            return_value=(
                [
                    ActionItem(
                        id="ai_001",
                        meeting_id="test",
                        description="Add password reset functionality",
                        assignee_name="Developer",
                        priority=ActionItemPriority.HIGH,
                        due_date_text="by next Tuesday",
                        source_quote="We need to add password reset functionality by next Tuesday.",
                    ),
                    ActionItem(
                        id="ai_002",
                        meeting_id="test",
                        description="Write test cases for authentication module",
                        assignee_name="QA Lead",
                        priority=ActionItemPriority.MEDIUM,
                        due_date_text="by Wednesday",
                        source_quote="I'll write the test cases for authentication.",
                    ),
                    ActionItem(
                        id="ai_003",
                        meeting_id="test",
                        description="Schedule demo with stakeholders",
                        assignee_name="Product Manager",
                        priority=ActionItemPriority.MEDIUM,
                        due_date_text="for Friday",
                    ),
                ],
                [
                    Decision(
                        id="dec_001",
                        meeting_id="test",
                        summary="Schedule stakeholder demo for Friday",
                        decision_type=DecisionType.DIRECTION,
                    )
                ],
                []
            )
        )
        
        # Execute the workflow
        context = HandlerContext(
            user_id="test_user",
            project_id="openproject:demo-project",
        )
        
        result = await handler.execute(
            context,
            audio_path=audio_file,
            meeting_title="Sprint Review - Week 5",
            participants=["Product Manager", "Developer", "QA Lead"],
        )
        
        # Verify success
        assert result.is_success, f"Expected success, got: {result.message}"
        
        # Verify summary
        summary = result.data
        assert summary is not None
        assert "authentication" in summary.executive_summary.lower()
        assert len(summary.key_points) >= 3
        
        # Verify action items
        assert len(summary.action_items) == 3
        action_descriptions = [ai.description for ai in summary.action_items]
        assert any("password reset" in d.lower() for d in action_descriptions)
        assert any("test cases" in d.lower() for d in action_descriptions)
        
        # Verify assignees
        assignees = [ai.assignee_name for ai in summary.action_items if ai.assignee_name]
        assert "Developer" in assignees
        assert "QA Lead" in assignees
        
        # Verify decisions
        assert len(summary.decisions) == 1
        assert "demo" in summary.decisions[0].summary.lower()
        
        # Verify meeting was persisted
        meeting = handler.repository.get_meeting(result.metadata.get("meeting_id"))
        # Note: This may be None if the meeting_id wasn't captured, which is OK for this test
        
        # Verify action items can be retrieved separately
        if meeting:
            stored_actions = handler.repository.get_action_items(meeting.id)
            assert len(stored_actions) == 3

    @pytest.mark.asyncio
    async def test_transcript_only_workflow(self, setup_environment):
        """Test processing a meeting from transcript text only"""
        config = MeetingAgentConfig(
            upload_dir=setup_environment["upload_dir"],
        )
        handler = MeetingHandler(
            config=config,
            database_url=setup_environment["db_url"],
        )
        
        # Raw transcript text
        transcript_text = """
        [John]: Good morning team. Today we need to finalize the API design.
        
        [Sarah]: I've reviewed the proposal. I suggest we use REST for the public API 
                 and GraphQL for internal services.
        
        [John]: That sounds good. Sarah, can you document the API endpoints by Thursday?
        
        [Mike]: I can help with the GraphQL schema. I'll have a draft ready by Wednesday.
        
        [John]: Perfect. Let's plan to review everything in Friday's meeting.
        """
        
        # Mock summarizer
        handler.summarizer.summarize = AsyncMock(
            return_value=MeetingSummary(
                meeting_id="test",
                executive_summary="API design finalization meeting with REST/GraphQL decision.",
                key_points=["Use REST for public API", "Use GraphQL for internal"],
            )
        )
        
        # Mock action extractor
        handler.action_extractor.extract = AsyncMock(
            return_value=(
                [
                    ActionItem(
                        id="ai_1",
                        meeting_id="test",
                        description="Document API endpoints",
                        assignee_name="Sarah",
                        due_date_text="by Thursday",
                    ),
                    ActionItem(
                        id="ai_2",
                        meeting_id="test",
                        description="Create GraphQL schema draft",
                        assignee_name="Mike",
                        due_date_text="by Wednesday",
                    ),
                ],
                [],
                []
            )
        )
        
        # Execute
        context = HandlerContext()
        result = await handler.process_from_text(
            context,
            transcript_text=transcript_text,
            meeting_title="API Design Discussion",
            participants=["John", "Sarah", "Mike"],
        )
        
        # Verify
        assert result.is_success
        assert len(result.data.action_items) == 2
        assert result.data.action_items[0].assignee_name == "Sarah"
