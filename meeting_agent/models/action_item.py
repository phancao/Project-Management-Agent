"""
Action item and decision models.

These models represent extracted action items, decisions,
and follow-ups from meeting analysis.
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class ActionItemStatus(str, Enum):
    """Status of an action item"""
    PENDING = "pending"         # Not started
    IN_PROGRESS = "in_progress" # Work has begun
    COMPLETED = "completed"     # Done
    CANCELLED = "cancelled"     # No longer needed


class ActionItemPriority(str, Enum):
    """Priority of an action item"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ActionItem(BaseModel):
    """
    An action item extracted from a meeting.
    
    Action items are tasks that need to be done, often
    with an assignee and deadline.
    """
    id: str = Field(..., description="Unique action item ID")
    meeting_id: str = Field(..., description="Source meeting ID")
    
    # Core fields
    description: str = Field(..., description="What needs to be done")
    context: Optional[str] = Field(None, description="Why this action is needed")
    
    # Assignment
    assignee_name: Optional[str] = Field(None, description="Who should do it")
    assignee_id: Optional[str] = Field(None, description="PM user ID if mapped")
    
    # Timeline
    due_date: Optional[date] = Field(None, description="When it's due")
    due_date_text: Optional[str] = Field(None, description="Original due date text from meeting")
    
    # Priority
    priority: ActionItemPriority = Field(default=ActionItemPriority.MEDIUM)
    
    # Status
    status: ActionItemStatus = Field(default=ActionItemStatus.PENDING)
    
    # Source reference
    source_quote: Optional[str] = Field(None, description="Exact quote from transcript")
    source_timestamp: Optional[float] = Field(None, description="Timestamp in meeting")
    
    # PM task link
    pm_task_id: Optional[str] = Field(None, description="Created PM task ID")
    pm_task_url: Optional[str] = Field(None, description="Link to PM task")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    confidence: float = Field(default=0.8, description="Extraction confidence 0-1")
    
    def to_pm_task_data(self) -> Dict[str, Any]:
        """Convert to PM task creation data"""
        return {
            "title": self.description[:200],  # Truncate for title
            "description": f"{self.description}\n\n**Context:** {self.context or 'From meeting discussion'}\n\n*Extracted from meeting*",
            "priority": self.priority.value,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "assignee_id": self.assignee_id,
            "metadata": {
                "source": "meeting",
                "meeting_id": self.meeting_id,
                "action_item_id": self.id,
            }
        }


class DecisionType(str, Enum):
    """Types of decisions"""
    APPROVAL = "approval"           # Something was approved
    REJECTION = "rejection"         # Something was rejected
    DIRECTION = "direction"         # Strategic direction set
    AGREEMENT = "agreement"         # Team agreed on something
    DEFERRAL = "deferral"          # Postponed decision
    ESCALATION = "escalation"       # Escalated to higher level


class Decision(BaseModel):
    """
    A decision made during a meeting.
    
    Decisions are important conclusions or agreements
    reached by the participants.
    """
    id: str = Field(..., description="Unique decision ID")
    meeting_id: str = Field(..., description="Source meeting ID")
    
    # Core fields
    summary: str = Field(..., description="What was decided")
    details: Optional[str] = Field(None, description="Additional context")
    decision_type: DecisionType = Field(default=DecisionType.AGREEMENT)
    
    # Participants
    decision_makers: List[str] = Field(default_factory=list, description="Who made the decision")
    stakeholders: List[str] = Field(default_factory=list, description="Who is affected")
    
    # Impact
    impact_areas: List[str] = Field(default_factory=list, description="Areas affected")
    
    # Source reference
    source_quote: Optional[str] = Field(None)
    source_timestamp: Optional[float] = Field(None)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    confidence: float = Field(default=0.8)


class FollowUp(BaseModel):
    """
    A follow-up item from a meeting.
    
    Follow-ups are topics that need further discussion
    or items to revisit later.
    """
    id: str = Field(..., description="Unique follow-up ID")
    meeting_id: str = Field(..., description="Source meeting ID")
    
    # Core fields
    topic: str = Field(..., description="What needs follow-up")
    reason: Optional[str] = Field(None, description="Why follow-up is needed")
    
    # When
    suggested_timing: Optional[str] = Field(None, description="When to follow up")
    
    # Source reference
    source_quote: Optional[str] = Field(None)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)


class MeetingSummary(BaseModel):
    """
    Complete analysis output for a meeting.
    
    Contains the executive summary, action items, decisions,
    and follow-ups extracted from the meeting.
    """
    meeting_id: str = Field(..., description="Source meeting ID")
    
    # Summary
    executive_summary: str = Field(..., description="2-3 sentence summary")
    key_points: List[str] = Field(default_factory=list, description="Main discussion points")
    
    # Extracted items
    action_items: List[ActionItem] = Field(default_factory=list)
    decisions: List[Decision] = Field(default_factory=list)
    follow_ups: List[FollowUp] = Field(default_factory=list)
    
    # Participants analysis
    participant_contributions: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Key contributions by participant"
    )
    
    # Topics covered
    topics: List[str] = Field(default_factory=list, description="Main topics discussed")
    
    # Sentiment
    overall_sentiment: Optional[str] = Field(None, description="positive, neutral, negative")
    
    # Metadata
    generated_at: datetime = Field(default_factory=datetime.now)
    model_used: Optional[str] = Field(None)
    
    def to_markdown(self) -> str:
        """Export summary as markdown"""
        lines = [
            f"# Meeting Summary",
            f"",
            f"## Executive Summary",
            f"{self.executive_summary}",
            f"",
            f"## Key Points",
        ]
        
        for point in self.key_points:
            lines.append(f"- {point}")
        
        if self.action_items:
            lines.append("")
            lines.append("## Action Items")
            for item in self.action_items:
                assignee = f" (@{item.assignee_name})" if item.assignee_name else ""
                due = f" - Due: {item.due_date}" if item.due_date else ""
                lines.append(f"- [ ] {item.description}{assignee}{due}")
        
        if self.decisions:
            lines.append("")
            lines.append("## Decisions Made")
            for decision in self.decisions:
                lines.append(f"- **{decision.decision_type.value.title()}**: {decision.summary}")
        
        if self.follow_ups:
            lines.append("")
            lines.append("## Follow-ups Needed")
            for fu in self.follow_ups:
                lines.append(f"- {fu.topic}")
        
        return "\n".join(lines)
