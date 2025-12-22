"""
Tests for Meeting Agent models.
"""

import pytest
from datetime import datetime, date
from meeting_agent.models import (
    Meeting,
    MeetingStatus,
    Transcript,
    TranscriptSegment,
    Participant,
    ParticipantRole,
    ActionItem,
    ActionItemPriority,
    ActionItemStatus,
    Decision,
    DecisionType,
    MeetingSummary,
)


class TestMeetingModels:
    """Tests for Meeting model"""

    def test_meeting_creation(self):
        """Test creating a basic meeting"""
        meeting = Meeting(
            id="mtg_123",
            title="Test Meeting",
        )
        
        assert meeting.id == "mtg_123"
        assert meeting.title == "Test Meeting"
        assert meeting.status == MeetingStatus.PENDING
        assert meeting.participants == []
        assert meeting.transcript is None

    def test_meeting_with_participants(self):
        """Test meeting with participants"""
        meeting = Meeting(
            id="mtg_456",
            title="Team Standup",
            participants=[
                Participant(name="Alice", role=ParticipantRole.HOST),
                Participant(name="Bob"),
            ]
        )
        
        assert len(meeting.participants) == 2
        assert meeting.participants[0].name == "Alice"
        assert meeting.participants[0].role == ParticipantRole.HOST
        assert meeting.participants[1].role == ParticipantRole.PARTICIPANT

    def test_meeting_duration(self):
        """Test meeting duration calculation"""
        meeting = Meeting(
            id="mtg_789",
            title="Long Meeting",
            actual_start=datetime(2024, 1, 1, 10, 0, 0),
            actual_end=datetime(2024, 1, 1, 11, 30, 0),
        )
        
        assert meeting.duration_minutes == 90.0


class TestTranscriptModels:
    """Tests for Transcript model"""

    def test_transcript_creation(self):
        """Test creating a transcript"""
        transcript = Transcript(
            meeting_id="mtg_123",
            language="en",
            segments=[
                TranscriptSegment(
                    id="seg_1",
                    speaker="Alice",
                    text="Hello everyone",
                    start_time=0.0,
                    end_time=2.0,
                ),
                TranscriptSegment(
                    id="seg_2",
                    speaker="Bob",
                    text="Hi Alice",
                    start_time=2.5,
                    end_time=4.0,
                ),
            ],
        )
        
        assert transcript.language == "en"
        assert len(transcript.segments) == 2

    def test_transcript_get_speakers(self):
        """Test getting unique speakers"""
        transcript = Transcript(
            meeting_id="mtg_123",
            segments=[
                TranscriptSegment(id="1", speaker="Alice", text="Hi", start_time=0, end_time=1),
                TranscriptSegment(id="2", speaker="Bob", text="Hello", start_time=1, end_time=2),
                TranscriptSegment(id="3", speaker="Alice", text="How are you?", start_time=2, end_time=3),
            ],
        )
        
        speakers = transcript.get_speakers()
        assert len(speakers) == 2
        assert "Alice" in speakers
        assert "Bob" in speakers

    def test_transcript_to_plain_text(self):
        """Test converting transcript to plain text"""
        transcript = Transcript(
            meeting_id="mtg_123",
            segments=[
                TranscriptSegment(id="1", speaker="Alice", text="Hello", start_time=0, end_time=1),
                TranscriptSegment(id="2", speaker="Bob", text="Hi there", start_time=1, end_time=2),
            ],
        )
        
        text = transcript.to_plain_text()
        assert "[Alice]: Hello" in text
        assert "[Bob]: Hi there" in text


class TestActionItemModels:
    """Tests for ActionItem model"""

    def test_action_item_creation(self):
        """Test creating an action item"""
        action = ActionItem(
            id="ai_001",
            meeting_id="mtg_123",
            description="Complete the report",
            assignee_name="Alice",
            due_date=date(2024, 1, 15),
            priority=ActionItemPriority.HIGH,
        )
        
        assert action.id == "ai_001"
        assert action.description == "Complete the report"
        assert action.priority == ActionItemPriority.HIGH
        assert action.status == ActionItemStatus.PENDING

    def test_action_item_to_pm_task_data(self):
        """Test converting action item to PM task format"""
        action = ActionItem(
            id="ai_002",
            meeting_id="mtg_456",
            description="Review the PR",
            context="Blocking the release",
            priority=ActionItemPriority.CRITICAL,
            due_date=date(2024, 1, 10),
        )
        
        task_data = action.to_pm_task_data()
        
        assert "Review the PR" in task_data["title"]
        assert task_data["priority"] == "critical"
        assert task_data["due_date"] == "2024-01-10"
        assert "meeting_id" in task_data["metadata"]


class TestMeetingSummaryModels:
    """Tests for MeetingSummary model"""

    def test_summary_to_markdown(self):
        """Test converting summary to markdown"""
        summary = MeetingSummary(
            meeting_id="mtg_123",
            executive_summary="A productive team meeting.",
            key_points=["Discussed Q1 goals", "Reviewed progress"],
            action_items=[
                ActionItem(
                    id="ai_1",
                    meeting_id="mtg_123",
                    description="Complete report",
                    assignee_name="Alice",
                )
            ],
            decisions=[
                Decision(
                    id="dec_1",
                    meeting_id="mtg_123",
                    summary="Approved the budget",
                    decision_type=DecisionType.APPROVAL,
                )
            ],
        )
        
        md = summary.to_markdown()
        
        assert "# Meeting Summary" in md
        assert "A productive team meeting" in md
        assert "Discussed Q1 goals" in md
        assert "Complete report" in md
        assert "Approved the budget" in md
