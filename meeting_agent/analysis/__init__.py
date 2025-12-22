"""
Meeting Analysis Package

This package provides analysis capabilities for processed meetings,
including summarization, action item extraction, and decision tracking.
"""

from meeting_agent.analysis.summarizer import MeetingSummarizer
from meeting_agent.analysis.action_extractor import ActionExtractor

__all__ = [
    'MeetingSummarizer',
    'ActionExtractor',
]
