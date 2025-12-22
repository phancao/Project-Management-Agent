"""
Test fixtures and configuration for meeting agent tests.
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
    Decision,
    DecisionType,
    FollowUp,
    MeetingSummary,
)


@pytest.fixture
def sample_transcript():
    """Create a sample transcript for testing"""
    return Transcript(
        meeting_id="mtg_test",
        language="en",
        segments=[
            TranscriptSegment(
                id="seg_1",
                speaker="Alice",
                text="Good morning everyone. Let's start the standup.",
                start_time=0.0,
                end_time=3.0,
            ),
            TranscriptSegment(
                id="seg_2",
                speaker="Bob",
                text="I finished the API integration yesterday. Today I'll work on testing.",
                start_time=3.5,
                end_time=8.0,
            ),
            TranscriptSegment(
                id="seg_3",
                speaker="Charlie",
                text="I'm blocked on the database migration. Can someone help?",
                start_time=8.5,
                end_time=12.0,
            ),
            TranscriptSegment(
                id="seg_4",
                speaker="Alice",
                text="Bob, can you help Charlie after this meeting? That should be your priority.",
                start_time=12.5,
                end_time=16.0,
            ),
        ],
        full_text="Good morning everyone. Let's start the standup. I finished the API integration yesterday. Today I'll work on testing. I'm blocked on the database migration. Can someone help? Bob, can you help Charlie after this meeting? That should be your priority.",
        word_count=50,
        duration_seconds=16.0,
    )


@pytest.fixture
def sample_meeting(sample_transcript):
    """Create a sample meeting for testing"""
    return Meeting(
        id="mtg_test_001",
        title="Daily Standup",
        description="Daily team sync",
        participants=[
            Participant(name="Alice", role=ParticipantRole.HOST, pm_user_id="user_alice"),
            Participant(name="Bob", pm_user_id="user_bob"),
            Participant(name="Charlie", pm_user_id="user_charlie"),
        ],
        transcript=sample_transcript,
        status=MeetingStatus.COMPLETED,
        actual_start=datetime(2024, 1, 10, 9, 0, 0),
        actual_end=datetime(2024, 1, 10, 9, 16, 0),
        project_id="openproject:demo-project",
    )


@pytest.fixture
def sample_action_items():
    """Create sample action items for testing"""
    return [
        ActionItem(
            id="ai_001",
            meeting_id="mtg_test_001",
            description="Help Charlie with database migration",
            assignee_name="Bob",
            assignee_id="user_bob",
            priority=ActionItemPriority.HIGH,
            context="Charlie is blocked",
            source_quote="Bob, can you help Charlie after this meeting?",
        ),
        ActionItem(
            id="ai_002",
            meeting_id="mtg_test_001",
            description="Complete API testing",
            assignee_name="Bob",
            assignee_id="user_bob",
            priority=ActionItemPriority.MEDIUM,
            due_date=date(2024, 1, 11),
            source_quote="Today I'll work on testing",
        ),
    ]


@pytest.fixture
def sample_summary(sample_action_items):
    """Create a sample meeting summary for testing"""
    return MeetingSummary(
        meeting_id="mtg_test_001",
        executive_summary="Quick standup discussing sprint progress. Bob completed API integration and will next help Charlie with a blocker.",
        key_points=[
            "Bob finished API integration",
            "Charlie is blocked on database migration",
            "Bob assigned to help Charlie",
        ],
        topics=["Sprint Progress", "Blockers", "Task Assignment"],
        action_items=sample_action_items,
        decisions=[
            Decision(
                id="dec_001",
                meeting_id="mtg_test_001",
                summary="Bob will prioritize helping Charlie",
                decision_type=DecisionType.DIRECTION,
                decision_makers=["Alice"],
            )
        ],
        follow_ups=[
            FollowUp(
                id="fu_001",
                meeting_id="mtg_test_001",
                topic="Database migration status",
                reason="Need to confirm blocker is resolved",
                suggested_timing="Tomorrow's standup",
            )
        ],
        participant_contributions={
            "Alice": ["Facilitated meeting", "Assigned Bob to help Charlie"],
            "Bob": ["Reported API completion", "Volunteered for testing"],
            "Charlie": ["Raised database blocker"],
        },
        overall_sentiment="neutral",
    )
