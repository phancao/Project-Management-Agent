"""
Database repository for Meeting Agent.

Provides CRUD operations for meetings and related data.
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from meeting_agent.database.models import (
    MeetingDB,
    ParticipantDB,
    TranscriptSegmentDB,
    ActionItemDB,
    DecisionDB,
    MeetingSummaryDB,
    create_database,
    get_session,
)
from meeting_agent.models import (
    Meeting,
    MeetingStatus,
    MeetingMetadata,
    Transcript,
    TranscriptSegment,
    Participant,
    ParticipantRole,
    ActionItem,
    ActionItemStatus,
    ActionItemPriority,
    Decision,
    DecisionType,
    FollowUp,
    MeetingSummary,
)


class MeetingRepository:
    """
    Repository for meeting database operations.
    """

    def __init__(self, database_url: str = "sqlite:///./data/meetings.db"):
        """Initialize repository with database"""
        self.engine = create_database(database_url)
        self._session = None

    @property
    def session(self) -> Session:
        """Get or create database session"""
        if self._session is None:
            self._session = get_session(self.engine)
        return self._session

    def close(self):
        """Close the session"""
        if self._session:
            self._session.close()
            self._session = None

    # Meeting CRUD
    
    def create_meeting(self, meeting: Meeting) -> Meeting:
        """Create a new meeting"""
        db_meeting = MeetingDB(
            id=meeting.id,
            title=meeting.title,
            description=meeting.description,
            status=meeting.status.value,
            project_id=meeting.project_id,
            file_path=meeting.metadata.file_path if meeting.metadata else None,
            created_at=meeting.created_at,
        )
        
        # Add participants
        for p in meeting.participants:
            db_meeting.participants.append(ParticipantDB(
                name=p.name,
                email=p.email,
                role=p.role.value if p.role else "participant",
                pm_user_id=p.pm_user_id,
            ))
        
        self.session.add(db_meeting)
        self.session.commit()
        return meeting

    def get_meeting(self, meeting_id: str) -> Optional[Meeting]:
        """Get a meeting by ID"""
        db_meeting = self.session.query(MeetingDB).filter_by(id=meeting_id).first()
        if not db_meeting:
            return None
        return self._to_meeting_model(db_meeting)

    def list_meetings(
        self,
        status: Optional[str] = None,
        project_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Meeting]:
        """List meetings with optional filters"""
        query = self.session.query(MeetingDB)
        
        if status:
            query = query.filter_by(status=status)
        if project_id:
            query = query.filter_by(project_id=project_id)
        
        query = query.order_by(desc(MeetingDB.created_at))
        query = query.limit(limit).offset(offset)
        
        return [self._to_meeting_model(m) for m in query.all()]

    def update_meeting_status(
        self,
        meeting_id: str,
        status: MeetingStatus,
        error_message: Optional[str] = None,
    ) -> bool:
        """Update meeting status"""
        db_meeting = self.session.query(MeetingDB).filter_by(id=meeting_id).first()
        if not db_meeting:
            return False
        
        db_meeting.status = status.value
        db_meeting.error_message = error_message
        db_meeting.updated_at = datetime.utcnow()
        
        if status == MeetingStatus.COMPLETED:
            db_meeting.processed_at = datetime.utcnow()
        
        self.session.commit()
        return True

    def delete_meeting(self, meeting_id: str) -> bool:
        """Delete a meeting and all related data"""
        db_meeting = self.session.query(MeetingDB).filter_by(id=meeting_id).first()
        if not db_meeting:
            return False
        
        self.session.delete(db_meeting)
        self.session.commit()
        return True

    # Transcript operations
    
    def save_transcript(self, meeting_id: str, transcript: Transcript) -> bool:
        """Save transcript segments"""
        db_meeting = self.session.query(MeetingDB).filter_by(id=meeting_id).first()
        if not db_meeting:
            return False
        
        # Clear existing segments
        self.session.query(TranscriptSegmentDB).filter_by(meeting_id=meeting_id).delete()
        
        # Add new segments
        for seg in transcript.segments:
            db_seg = TranscriptSegmentDB(
                id=seg.id,
                meeting_id=meeting_id,
                speaker=seg.speaker,
                speaker_id=seg.speaker_id,
                text=seg.text,
                start_time=seg.start_time,
                end_time=seg.end_time,
                confidence=seg.confidence,
            )
            self.session.add(db_seg)
        
        db_meeting.duration_seconds = transcript.duration_seconds
        self.session.commit()
        return True

    def get_transcript(self, meeting_id: str) -> Optional[Transcript]:
        """Get transcript for a meeting"""
        segments = self.session.query(TranscriptSegmentDB).filter_by(
            meeting_id=meeting_id
        ).order_by(TranscriptSegmentDB.start_time).all()
        
        if not segments:
            return None
        
        return Transcript(
            meeting_id=meeting_id,
            segments=[
                TranscriptSegment(
                    id=s.id,
                    speaker=s.speaker,
                    speaker_id=s.speaker_id,
                    text=s.text,
                    start_time=s.start_time,
                    end_time=s.end_time,
                    confidence=s.confidence,
                )
                for s in segments
            ],
            duration_seconds=segments[-1].end_time if segments else 0,
        )

    # Action Items
    
    def save_action_items(self, meeting_id: str, items: List[ActionItem]) -> bool:
        """Save action items for a meeting"""
        # Clear existing
        self.session.query(ActionItemDB).filter_by(meeting_id=meeting_id).delete()
        
        for item in items:
            db_item = ActionItemDB(
                id=item.id,
                meeting_id=meeting_id,
                description=item.description,
                context=item.context,
                assignee_name=item.assignee_name,
                assignee_id=item.assignee_id,
                due_date=item.due_date,
                due_date_text=item.due_date_text,
                priority=item.priority.value,
                status=item.status.value,
                source_quote=item.source_quote,
                source_timestamp=item.source_timestamp,
                pm_task_id=item.pm_task_id,
                pm_task_url=item.pm_task_url,
                confidence=item.confidence,
            )
            self.session.add(db_item)
        
        self.session.commit()
        return True

    def get_action_items(self, meeting_id: str) -> List[ActionItem]:
        """Get action items for a meeting"""
        db_items = self.session.query(ActionItemDB).filter_by(meeting_id=meeting_id).all()
        
        return [
            ActionItem(
                id=i.id,
                meeting_id=i.meeting_id,
                description=i.description,
                context=i.context,
                assignee_name=i.assignee_name,
                assignee_id=i.assignee_id,
                due_date=i.due_date,
                due_date_text=i.due_date_text,
                priority=ActionItemPriority(i.priority),
                status=ActionItemStatus(i.status),
                source_quote=i.source_quote,
                source_timestamp=i.source_timestamp,
                pm_task_id=i.pm_task_id,
                pm_task_url=i.pm_task_url,
                confidence=i.confidence,
                created_at=i.created_at,
            )
            for i in db_items
        ]

    def update_action_item_task(
        self,
        action_item_id: str,
        pm_task_id: str,
        pm_task_url: Optional[str] = None,
    ) -> bool:
        """Update action item with created PM task"""
        db_item = self.session.query(ActionItemDB).filter_by(id=action_item_id).first()
        if not db_item:
            return False
        
        db_item.pm_task_id = pm_task_id
        db_item.pm_task_url = pm_task_url
        self.session.commit()
        return True

    # Summary
    
    def save_summary(self, meeting_id: str, summary: MeetingSummary) -> bool:
        """Save meeting summary"""
        # Delete existing
        self.session.query(MeetingSummaryDB).filter_by(meeting_id=meeting_id).delete()
        
        db_summary = MeetingSummaryDB(
            meeting_id=meeting_id,
            executive_summary=summary.executive_summary,
            key_points=summary.key_points,
            topics=summary.topics,
            participant_contributions=summary.participant_contributions,
            overall_sentiment=summary.overall_sentiment,
            model_used=summary.model_used,
            generated_at=summary.generated_at,
        )
        self.session.add(db_summary)
        self.session.commit()
        return True

    def get_summary(self, meeting_id: str) -> Optional[MeetingSummary]:
        """Get meeting summary"""
        db_summary = self.session.query(MeetingSummaryDB).filter_by(meeting_id=meeting_id).first()
        if not db_summary:
            return None
        
        # Get action items and decisions
        action_items = self.get_action_items(meeting_id)
        decisions = self._get_decisions(meeting_id)
        
        return MeetingSummary(
            meeting_id=meeting_id,
            executive_summary=db_summary.executive_summary,
            key_points=db_summary.key_points or [],
            topics=db_summary.topics or [],
            participant_contributions=db_summary.participant_contributions or {},
            overall_sentiment=db_summary.overall_sentiment,
            model_used=db_summary.model_used,
            action_items=action_items,
            decisions=decisions,
            generated_at=db_summary.generated_at,
        )

    # Decisions
    
    def save_decisions(self, meeting_id: str, decisions: List[Decision]) -> bool:
        """Save decisions for a meeting"""
        self.session.query(DecisionDB).filter_by(meeting_id=meeting_id).delete()
        
        for dec in decisions:
            db_dec = DecisionDB(
                id=dec.id,
                meeting_id=meeting_id,
                summary=dec.summary,
                details=dec.details,
                decision_type=dec.decision_type.value,
                decision_makers=dec.decision_makers,
                stakeholders=dec.stakeholders,
                impact_areas=dec.impact_areas,
                source_quote=dec.source_quote,
                source_timestamp=dec.source_timestamp,
                confidence=dec.confidence,
            )
            self.session.add(db_dec)
        
        self.session.commit()
        return True

    def _get_decisions(self, meeting_id: str) -> List[Decision]:
        """Get decisions for a meeting"""
        db_decisions = self.session.query(DecisionDB).filter_by(meeting_id=meeting_id).all()
        
        return [
            Decision(
                id=d.id,
                meeting_id=d.meeting_id,
                summary=d.summary,
                details=d.details,
                decision_type=DecisionType(d.decision_type),
                decision_makers=d.decision_makers or [],
                stakeholders=d.stakeholders or [],
                impact_areas=d.impact_areas or [],
                source_quote=d.source_quote,
                source_timestamp=d.source_timestamp,
                confidence=d.confidence,
                created_at=d.created_at,
            )
            for d in db_decisions
        ]

    # Helpers
    
    def _to_meeting_model(self, db_meeting: MeetingDB) -> Meeting:
        """Convert DB model to domain model"""
        return Meeting(
            id=db_meeting.id,
            title=db_meeting.title,
            description=db_meeting.description,
            status=MeetingStatus(db_meeting.status),
            error_message=db_meeting.error_message,
            scheduled_start=db_meeting.scheduled_start,
            scheduled_end=db_meeting.scheduled_end,
            actual_start=db_meeting.actual_start,
            actual_end=db_meeting.actual_end,
            participants=[
                Participant(
                    name=p.name,
                    email=p.email,
                    role=ParticipantRole(p.role) if p.role else ParticipantRole.PARTICIPANT,
                    pm_user_id=p.pm_user_id,
                    speaking_time_seconds=p.speaking_time_seconds,
                )
                for p in db_meeting.participants
            ],
            project_id=db_meeting.project_id,
            metadata=MeetingMetadata(
                file_path=db_meeting.file_path,
                file_size_bytes=db_meeting.file_size_bytes,
                audio_format=db_meeting.audio_format,
                platform=db_meeting.platform,
                custom=db_meeting.extra_metadata or {},
            ),
            created_at=db_meeting.created_at,
            updated_at=db_meeting.updated_at,
            processed_at=db_meeting.processed_at,
        )
