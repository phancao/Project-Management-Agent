"""
Data models for meetings.

These models represent meeting data structure including
transcripts, segments, participants, and metadata.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class MeetingStatus(str, Enum):
    """Status of meeting processing"""
    PENDING = "pending"           # Uploaded but not processed
    TRANSCRIBING = "transcribing" # Transcription in progress
    ANALYZING = "analyzing"       # Analysis in progress
    COMPLETED = "completed"       # Fully processed
    FAILED = "failed"             # Processing failed


class ParticipantRole(str, Enum):
    """Role of a meeting participant"""
    HOST = "host"
    PRESENTER = "presenter"
    PARTICIPANT = "participant"
    GUEST = "guest"


class Participant(BaseModel):
    """A meeting participant"""
    id: Optional[str] = Field(None, description="Participant ID (from meeting platform)")
    name: str = Field(..., description="Participant display name")
    email: Optional[str] = Field(None, description="Participant email if known")
    role: ParticipantRole = Field(default=ParticipantRole.PARTICIPANT)
    pm_user_id: Optional[str] = Field(None, description="Linked PM system user ID")
    speaking_time_seconds: Optional[float] = Field(None, description="Total speaking time")
    
    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude_none=True)


class TranscriptSegment(BaseModel):
    """A segment of the meeting transcript"""
    id: str = Field(..., description="Segment ID")
    speaker: Optional[str] = Field(None, description="Speaker name if identified")
    speaker_id: Optional[str] = Field(None, description="Speaker participant ID")
    text: str = Field(..., description="Transcribed text")
    start_time: float = Field(..., description="Start time in seconds")
    end_time: float = Field(..., description="End time in seconds")
    confidence: Optional[float] = Field(None, description="Transcription confidence 0-1")
    
    @property
    def duration(self) -> float:
        """Duration of this segment in seconds"""
        return self.end_time - self.start_time


class Transcript(BaseModel):
    """Complete meeting transcript"""
    meeting_id: str = Field(..., description="Parent meeting ID")
    language: str = Field(default="en", description="Detected language code")
    segments: List[TranscriptSegment] = Field(default_factory=list)
    full_text: Optional[str] = Field(None, description="Full transcript as plain text")
    word_count: int = Field(default=0)
    duration_seconds: float = Field(default=0)
    
    def get_text_by_speaker(self, speaker: str) -> str:
        """Get all text spoken by a specific speaker"""
        return " ".join(
            seg.text for seg in self.segments 
            if seg.speaker == speaker
        )
    
    def get_speakers(self) -> List[str]:
        """Get list of unique speakers"""
        return list(set(
            seg.speaker for seg in self.segments 
            if seg.speaker
        ))
    
    def to_plain_text(self) -> str:
        """Convert to plain text format"""
        if self.full_text:
            return self.full_text
        
        lines = []
        for seg in self.segments:
            prefix = f"[{seg.speaker}]: " if seg.speaker else ""
            lines.append(f"{prefix}{seg.text}")
        return "\n".join(lines)


class MeetingMetadata(BaseModel):
    """Metadata about a meeting"""
    platform: Optional[str] = Field(None, description="Meeting platform (zoom, teams, etc.)")
    meeting_url: Optional[str] = Field(None, description="Original meeting URL")
    recording_url: Optional[str] = Field(None, description="Recording URL if available")
    file_path: Optional[str] = Field(None, description="Local file path if uploaded")
    file_size_bytes: Optional[int] = Field(None)
    audio_format: Optional[str] = Field(None, description="Audio format (mp3, wav, etc.)")
    sample_rate: Optional[int] = Field(None)
    custom: Dict[str, Any] = Field(default_factory=dict)


class Meeting(BaseModel):
    """
    Represents a meeting with all associated data.
    
    This is the primary model for meeting processing.
    """
    id: str = Field(..., description="Unique meeting ID")
    title: str = Field(..., description="Meeting title")
    description: Optional[str] = Field(None, description="Meeting description")
    
    # Timing
    scheduled_start: Optional[datetime] = Field(None, description="Scheduled start time")
    scheduled_end: Optional[datetime] = Field(None, description="Scheduled end time")
    actual_start: Optional[datetime] = Field(None, description="Actual start time")
    actual_end: Optional[datetime] = Field(None, description="Actual end time")
    
    # Status
    status: MeetingStatus = Field(default=MeetingStatus.PENDING)
    error_message: Optional[str] = Field(None)
    
    # Participants
    participants: List[Participant] = Field(default_factory=list)
    
    # Transcript
    transcript: Optional[Transcript] = Field(None)
    
    # Metadata
    metadata: MeetingMetadata = Field(default_factory=MeetingMetadata)
    
    # Processing timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    processed_at: Optional[datetime] = Field(None)
    
    # PM Integration
    project_id: Optional[str] = Field(None, description="Linked PM project ID")
    
    @property
    def duration_minutes(self) -> Optional[float]:
        """Meeting duration in minutes"""
        if self.actual_start and self.actual_end:
            delta = self.actual_end - self.actual_start
            return delta.total_seconds() / 60
        return None
    
    def to_summary_dict(self) -> Dict[str, Any]:
        """Return a summary dict for display"""
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status.value,
            "participants_count": len(self.participants),
            "duration_minutes": self.duration_minutes,
            "created_at": self.created_at.isoformat(),
        }
