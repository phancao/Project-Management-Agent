"""
Meeting summarization.

Generates executive summaries, key points, and topic analysis
from meeting transcripts using LLMs.
"""

import logging
import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from meeting_agent.models.meeting import Meeting, Transcript
from meeting_agent.models.action_item import MeetingSummary

logger = logging.getLogger(__name__)


@dataclass
class SummaryConfig:
    """Configuration for summarization"""
    model: str = "gpt-4"
    max_key_points: int = 10
    max_topics: int = 8
    include_participant_analysis: bool = True
    language: str = "en"


class MeetingSummarizer:
    """
    Summarizes meeting transcripts using LLMs.
    
    Produces an executive summary, key points, topics,
    and participant contribution analysis.
    """
    
    def __init__(self, config: Optional[SummaryConfig] = None):
        """
        Initialize summarizer.
        
        Args:
            config: Summarization configuration
        """
        self.config = config or SummaryConfig()
    
    async def summarize(
        self,
        meeting: Meeting,
        existing_summary: Optional[MeetingSummary] = None,
    ) -> MeetingSummary:
        """
        Generate a summary for a meeting.
        
        Args:
            meeting: The meeting to summarize
            existing_summary: Optional existing summary to update
            
        Returns:
            MeetingSummary with analysis
        """
        if not meeting.transcript:
            raise ValueError("Meeting has no transcript")
        
        transcript_text = meeting.transcript.to_plain_text()
        
        # Build prompt
        prompt = self._build_summary_prompt(meeting, transcript_text)
        
        # Call LLM
        try:
            response = await self._call_llm(prompt)
            parsed = self._parse_response(response)
            
            summary = MeetingSummary(
                meeting_id=meeting.id,
                executive_summary=parsed.get("summary", ""),
                key_points=parsed.get("key_points", []),
                topics=parsed.get("topics", []),
                participant_contributions=parsed.get("participant_contributions", {}),
                overall_sentiment=parsed.get("sentiment"),
                model_used=self.config.model,
                # Action items and decisions will be filled by other analyzers
                action_items=existing_summary.action_items if existing_summary else [],
                decisions=existing_summary.decisions if existing_summary else [],
                follow_ups=existing_summary.follow_ups if existing_summary else [],
            )
            
            return summary
            
        except Exception as e:
            logger.exception(f"Summarization failed: {e}")
            raise
    
    def _build_summary_prompt(
        self,
        meeting: Meeting,
        transcript_text: str,
    ) -> str:
        """Build the summarization prompt"""
        participants = ", ".join([p.name for p in meeting.participants]) if meeting.participants else "Unknown"
        
        prompt = f"""Analyze the following meeting transcript and provide a comprehensive summary.

## Meeting Information
- Title: {meeting.title}
- Participants: {participants}
- Duration: {meeting.duration_minutes or 'Unknown'} minutes

## Transcript
{transcript_text[:50000]}  # Truncate if too long

## Instructions
Provide your analysis in the following JSON format:

```json
{{
    "summary": "A 2-3 sentence executive summary of the meeting",
    "key_points": [
        "Key point 1",
        "Key point 2",
        "... (up to {self.config.max_key_points} points)"
    ],
    "topics": [
        "Topic 1",
        "Topic 2",
        "... (up to {self.config.max_topics} topics)"
    ],
    "participant_contributions": {{
        "Participant Name": ["Their key contribution 1", "Their key contribution 2"],
        "Another Participant": ["Their contributions"]
    }},
    "sentiment": "positive|neutral|negative"
}}
```

Focus on:
1. What were the main discussion points?
2. What conclusions were reached?
3. What topics need further discussion?
4. Who contributed what to the discussion?

Return ONLY the JSON, no additional text."""

        return prompt
    
    async def _call_llm(self, prompt: str) -> str:
        """Call the LLM with the prompt"""
        try:
            from openai import AsyncOpenAI
            import os
            
            client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            response = await client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": "You are a meeting analysis expert. Analyze transcripts and provide structured summaries."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000,
            )
            
            return response.choices[0].message.content
            
        except ImportError:
            raise ImportError("OpenAI library not installed. Run: pip install openai")
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse the LLM response into structured data"""
        # Try to extract JSON from response
        try:
            # Look for JSON block
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
            # Return basic structure
            return {
                "summary": response[:500] if response else "Summary not available",
                "key_points": [],
                "topics": [],
                "participant_contributions": {},
            }
