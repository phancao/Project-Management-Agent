"""
Configuration for Meeting Agent.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum
import os


class AudioSourceType(str, Enum):
    """Types of audio sources for meetings"""
    FILE_UPLOAD = "file_upload"      # Upload audio/video files
    STREAM = "stream"                 # Real-time streaming
    ZOOM = "zoom"                     # Zoom integration
    TEAMS = "teams"                   # Microsoft Teams
    MEET = "meet"                     # Google Meet


class TranscriptionProvider(str, Enum):
    """Transcription service providers"""
    WHISPER = "whisper"               # OpenAI Whisper
    WHISPER_LOCAL = "whisper_local"   # Local Whisper model
    DEEPGRAM = "deepgram"             # Deepgram API
    ASSEMBLY_AI = "assembly_ai"       # AssemblyAI


@dataclass
class MeetingAgentConfig:
    """
    Configuration for the Meeting Agent.
    
    Load from environment variables or pass explicitly.
    """
    
    # Audio processing
    audio_source: AudioSourceType = AudioSourceType.FILE_UPLOAD
    supported_audio_formats: List[str] = field(
        default_factory=lambda: ["mp3", "wav", "webm", "m4a", "ogg"]
    )
    max_audio_size_mb: int = 500
    
    # Transcription
    transcription_provider: TranscriptionProvider = TranscriptionProvider.WHISPER
    whisper_model: str = "whisper-1"  # OpenAI model
    whisper_language: Optional[str] = None  # Auto-detect if None
    
    # Analysis
    summarization_model: str = "gpt-4"
    action_extraction_model: str = "gpt-4"
    max_transcript_tokens: int = 100000
    
    # PM Integration
    default_pm_provider_id: Optional[str] = None
    default_project_id: Optional[str] = None
    auto_create_tasks: bool = False  # Require confirmation by default
    
    # Storage
    upload_dir: str = "./uploads/meetings"
    transcript_dir: str = "./data/transcripts"
    
    # Server
    server_host: str = "0.0.0.0"
    server_port: int = 8081
    
    @classmethod
    def from_env(cls) -> "MeetingAgentConfig":
        """Load configuration from environment variables"""
        return cls(
            audio_source=AudioSourceType(
                os.getenv("MEETING_AUDIO_SOURCE", "file_upload")
            ),
            transcription_provider=TranscriptionProvider(
                os.getenv("MEETING_TRANSCRIPTION_PROVIDER", "whisper")
            ),
            whisper_model=os.getenv("WHISPER_MODEL", "whisper-1"),
            whisper_language=os.getenv("WHISPER_LANGUAGE"),
            summarization_model=os.getenv("MEETING_SUMMARY_MODEL", "gpt-4"),
            action_extraction_model=os.getenv("MEETING_ACTION_MODEL", "gpt-4"),
            default_pm_provider_id=os.getenv("DEFAULT_PM_PROVIDER_ID"),
            default_project_id=os.getenv("DEFAULT_PROJECT_ID"),
            auto_create_tasks=os.getenv("MEETING_AUTO_CREATE_TASKS", "false").lower() == "true",
            upload_dir=os.getenv("MEETING_UPLOAD_DIR", "./uploads/meetings"),
            transcript_dir=os.getenv("MEETING_TRANSCRIPT_DIR", "./data/transcripts"),
            server_host=os.getenv("MEETING_SERVER_HOST", "0.0.0.0"),
            server_port=int(os.getenv("MEETING_SERVER_PORT", "8081")),
        )
