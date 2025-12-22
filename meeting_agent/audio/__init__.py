"""
Audio Processing Package

This package handles audio processing for meeting recordings,
including format conversion, audio analysis, and preparation
for transcription.
"""

from meeting_agent.audio.processor import AudioProcessor
from meeting_agent.audio.transcriber import Transcriber, TranscriptionResult

__all__ = [
    'AudioProcessor',
    'Transcriber',
    'TranscriptionResult',
]
