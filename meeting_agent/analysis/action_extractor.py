"""
Action item extraction from meetings.

Extracts action items, decisions, and follow-ups from
meeting transcripts using LLMs.
"""

import logging
import json
import uuid
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from meeting_agent.models.meeting import Meeting, Transcript
from meeting_agent.models.action_item import (
    ActionItem,
    ActionItemPriority,
    Decision,
    DecisionType,
    FollowUp,
)

logger = logging.getLogger(__name__)


@dataclass
class ExtractionConfig:
    """Configuration for action extraction"""
    model: str = "gpt-4"
    extract_decisions: bool = True
    extract_follow_ups: bool = True
    min_confidence: float = 0.5


class ActionExtractor:
    """
    Extracts action items from meeting transcripts.
    
    Uses LLMs to identify tasks, assignments, deadlines,
    decisions, and follow-up items.
    """
    
    def __init__(self, config: Optional[ExtractionConfig] = None):
        """
        Initialize extractor.
        
        Args:
            config: Extraction configuration
        """
        self.config = config or ExtractionConfig()
    
    async def extract(
        self,
        meeting: Meeting,
        participant_mapping: Optional[Dict[str, str]] = None,
        project_context: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
    ) -> tuple[List[ActionItem], List[Decision], List[FollowUp]]:
        """
        Extract action items, decisions, and follow-ups from a meeting.
        
        Args:
            meeting: The meeting to analyze
            participant_mapping: Optional mapping of names to PM user IDs
            project_context: Optional context about the project
            
        Returns:
            Tuple of (action_items, decisions, follow_ups)
        """
        if not meeting.transcript:
            raise ValueError("Meeting has no transcript")
        
        transcript_text = meeting.transcript.to_plain_text()
        participants = [p.name for p in meeting.participants]
        
        # Build prompt
        prompt = self._build_extraction_prompt(
            meeting, 
            transcript_text,
            participants,
            project_context,
        )
        
        # Call LLM
        try:
            response = await self._call_llm(prompt, api_key)
            parsed = self._parse_response(response)
            
            # Convert to models
            action_items = self._parse_action_items(
                parsed.get("action_items", []),
                meeting.id,
                participant_mapping,
            )
            
            decisions = []
            if self.config.extract_decisions:
                decisions = self._parse_decisions(
                    parsed.get("decisions", []),
                    meeting.id,
                )
            
            follow_ups = []
            if self.config.extract_follow_ups:
                follow_ups = self._parse_follow_ups(
                    parsed.get("follow_ups", []),
                    meeting.id,
                )
            
            return action_items, decisions, follow_ups
            
        except Exception as e:
            logger.exception(f"Action extraction failed: {e}")
            raise
    
    def _build_extraction_prompt(
        self,
        meeting: Meeting,
        transcript_text: str,
        participants: List[str],
        project_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build the extraction prompt"""
        participants_str = ", ".join(participants) if participants else "Unknown"
        project_info = ""
        if project_context:
            project_info = f"""
## Project Context
- Project: {project_context.get('name', 'Unknown')}
- Description: {project_context.get('description', '')}
- Known Project Participants: {', '.join([p['name'] for p in project_context.get('participants', [])]) if project_context.get('participants') else 'Unknown'}
"""
        
        prompt = f"""Analyze the following meeting transcript and extract action items, decisions, and follow-ups.

## Meeting Information
- Title: {meeting.title}
- Participants: {participants_str}
{project_info}
## Transcript
{transcript_text[:50000]}

## Instructions
Extract the following from the transcript:

1. **Action Items**: Tasks that need to be done
   - Look for explicit assignments ("John will...", "Can you...")
   - Look for commitments ("I'll have it done by...")
   - Look for requirements ("We need to...")

2. **Decisions**: Conclusions or agreements reached
   - Approvals or rejections
   - Strategic directions
   - Team agreements

3. **Follow-ups**: Topics needing future discussion

Return your analysis in this JSON format:

```json
{{
    "action_items": [
        {{
            "description": "Clear description of what needs to be done",
            "assignee": "Person's name or null if unassigned",
            "due_date": "YYYY-MM-DD or null",
            "due_date_text": "Original text like 'by Friday' or 'next week'",
            "priority": "high|medium|low",
            "context": "Brief context why this is needed",
            "source_quote": "Exact quote from transcript"
        }}
    ],
    "decisions": [
        {{
            "summary": "What was decided",
            "type": "approval|rejection|direction|agreement|deferral",
            "decision_makers": ["Name1", "Name2"],
            "source_quote": "Exact quote"
        }}
    ],
    "follow_ups": [
        {{
            "topic": "What needs follow-up",
            "reason": "Why it needs follow-up",
            "suggested_timing": "When to follow up"
        }}
    ]
}}
```

Be thorough but only include items with clear evidence in the transcript.
Return ONLY the JSON, no additional text."""

        return prompt
    
    async def _call_llm(self, prompt: str, api_key: Optional[str] = None) -> str:
        """Call the LLM with the prompt"""
        try:
            from openai import AsyncOpenAI
            import os
            
            client = AsyncOpenAI(api_key=api_key)
            
            response = await client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing meeting transcripts and extracting actionable items. Be thorough and precise."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=3000,
            )
            
            return response.choices[0].message.content
            
        except ImportError:
            raise ImportError("OpenAI library not installed. Run: pip install openai")
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse the LLM response"""
        try:
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                json_str = response.strip()
            
            return json.loads(json_str)
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            return {"action_items": [], "decisions": [], "follow_ups": []}
    
    def _parse_action_items(
        self,
        items: List[Dict],
        meeting_id: str,
        participant_mapping: Optional[Dict[str, str]],
    ) -> List[ActionItem]:
        """Parse action items from extracted data"""
        action_items = []
        
        for item in items:
            assignee_name = item.get("assignee")
            assignee_id = None
            
            if assignee_name and participant_mapping:
                assignee_id = participant_mapping.get(assignee_name)
            
            # Parse due date
            due_date = None
            if item.get("due_date"):
                try:
                    due_date = date.fromisoformat(item["due_date"])
                except ValueError:
                    pass
            
            # Parse priority
            priority_str = item.get("priority", "medium").lower()
            try:
                priority = ActionItemPriority(priority_str)
            except ValueError:
                priority = ActionItemPriority.MEDIUM
            
            action_items.append(ActionItem(
                id=f"ai_{uuid.uuid4().hex[:8]}",
                meeting_id=meeting_id,
                description=item.get("description", ""),
                context=item.get("context"),
                assignee_name=assignee_name,
                assignee_id=assignee_id,
                due_date=due_date,
                due_date_text=item.get("due_date_text"),
                priority=priority,
                source_quote=item.get("source_quote"),
            ))
        
        return action_items
    
    def _parse_decisions(
        self,
        items: List[Dict],
        meeting_id: str,
    ) -> List[Decision]:
        """Parse decisions from extracted data"""
        decisions = []
        
        for item in items:
            decision_type_str = item.get("type", "agreement").lower()
            try:
                decision_type = DecisionType(decision_type_str)
            except ValueError:
                decision_type = DecisionType.AGREEMENT
            
            decisions.append(Decision(
                id=f"dec_{uuid.uuid4().hex[:8]}",
                meeting_id=meeting_id,
                summary=item.get("summary", ""),
                decision_type=decision_type,
                decision_makers=item.get("decision_makers", []),
                source_quote=item.get("source_quote"),
            ))
        
        return decisions
    
    def _parse_follow_ups(
        self,
        items: List[Dict],
        meeting_id: str,
    ) -> List[FollowUp]:
        """Parse follow-ups from extracted data"""
        follow_ups = []
        
        for item in items:
            follow_ups.append(FollowUp(
                id=f"fu_{uuid.uuid4().hex[:8]}",
                meeting_id=meeting_id,
                topic=item.get("topic", ""),
                reason=item.get("reason"),
                suggested_timing=item.get("suggested_timing"),
            ))
        
        return follow_ups
