"""
Speech-to-text transcription for meetings.

Supports multiple transcription providers including
OpenAI Whisper, Deepgram, and AssemblyAI.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any

from meeting_agent.config import TranscriptionProvider
from meeting_agent.models.meeting import Transcript, TranscriptSegment

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """Result from transcription service"""
    success: bool
    transcript: Optional[Transcript] = None
    error: Optional[str] = None
    raw_response: Dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0
    language: str = "en"


class BaseTranscriber(ABC):
    """Base class for transcription providers"""
    
    @abstractmethod
    async def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        **kwargs
    ) -> TranscriptionResult:
        """
        Transcribe an audio file.
        
        Args:
            audio_path: Path to audio file
            language: Language code (e.g., "en", "vi") or None for auto-detect
            **kwargs: Provider-specific options
            
        Returns:
            TranscriptionResult with transcript or error
        """
        pass


class WhisperTranscriber(BaseTranscriber):
    """
    OpenAI Whisper API transcriber.
    
    Uses the OpenAI Whisper API for high-quality transcription
    with speaker diarization support.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "whisper-1",
    ):
        """
        Initialize Whisper transcriber.
        
        Args:
            api_key: OpenAI API key (uses OPENAI_API_KEY env if not provided)
            model: Whisper model to use
        """
        import os
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        
        if not self.api_key:
            logger.warning("No OpenAI API key found")
    
    async def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        response_format: str = "verbose_json",
        **kwargs
    ) -> TranscriptionResult:
        """Transcribe using OpenAI Whisper API"""
        try:
            from openai import AsyncOpenAI
            
            client = AsyncOpenAI(api_key=self.api_key)
            
            with open(audio_path, "rb") as audio_file:
                # Call Whisper API
                params = {
                    "model": self.model,
                    "file": audio_file,
                    "response_format": response_format,
                }
                
                if language:
                    params["language"] = language
                
                response = await client.audio.transcriptions.create(**params)
            
            # Parse response
            if response_format == "verbose_json":
                segments = self._parse_verbose_response(response, audio_path)
            else:
                segments = [TranscriptSegment(
                    id="seg_0",
                    text=response.text if hasattr(response, 'text') else str(response),
                    start_time=0,
                    end_time=0,
                )]
            
            transcript = Transcript(
                meeting_id="",  # Will be set by caller
                language=getattr(response, 'language', language or 'en'),
                segments=segments,
                full_text=getattr(response, 'text', ''),
                word_count=len(getattr(response, 'text', '').split()),
                duration_seconds=getattr(response, 'duration', 0),
            )
            
            return TranscriptionResult(
                success=True,
                transcript=transcript,
                duration_seconds=transcript.duration_seconds,
                language=transcript.language,
                raw_response=response.model_dump() if hasattr(response, 'model_dump') else {},
            )
            
        except ImportError:
            return TranscriptionResult(
                success=False,
                error="OpenAI library not installed. Run: pip install openai",
            )
        except Exception as e:
            logger.exception(f"Whisper transcription failed: {e}")
            return TranscriptionResult(
                success=False,
                error=str(e),
            )
    
    def _parse_verbose_response(
        self,
        response: Any,
        audio_path: str,
    ) -> List[TranscriptSegment]:
        """Parse verbose JSON response into segments"""
        segments = []
        
        if hasattr(response, 'segments'):
            for i, seg in enumerate(response.segments):
                segments.append(TranscriptSegment(
                    id=f"seg_{i}",
                    text=seg.get('text', '') if isinstance(seg, dict) else getattr(seg, 'text', ''),
                    start_time=seg.get('start', 0) if isinstance(seg, dict) else getattr(seg, 'start', 0),
                    end_time=seg.get('end', 0) if isinstance(seg, dict) else getattr(seg, 'end', 0),
                    confidence=seg.get('avg_logprob') if isinstance(seg, dict) else getattr(seg, 'avg_logprob', None),
                ))
        
        return segments


class LocalWhisperTranscriber(BaseTranscriber):
    """
    Local Whisper model transcriber.
    
    Runs Whisper locally for privacy-sensitive transcription.
    Requires the whisper package to be installed.
    """
    
    def __init__(self, model_size: str = "base"):
        """
        Initialize local Whisper.
        
        Args:
            model_size: Model size (tiny, base, small, medium, large)
        """
        self.model_size = model_size
        self._model = None
    
    def _load_model(self):
        """Load the Whisper model lazily"""
        if self._model is None:
            try:
                import whisper
                self._model = whisper.load_model(self.model_size)
            except ImportError:
                raise ImportError("whisper not installed. Run: pip install openai-whisper")
        return self._model
    
    async def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        **kwargs
    ) -> TranscriptionResult:
        """Transcribe using local Whisper model"""
        try:
            import asyncio
            
            model = self._load_model()
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: model.transcribe(
                    audio_path,
                    language=language,
                    verbose=False,
                )
            )
            
            # Parse result
            segments = []
            for i, seg in enumerate(result.get("segments", [])):
                segments.append(TranscriptSegment(
                    id=f"seg_{i}",
                    text=seg["text"].strip(),
                    start_time=seg["start"],
                    end_time=seg["end"],
                ))
            
            transcript = Transcript(
                meeting_id="",
                language=result.get("language", language or "en"),
                segments=segments,
                full_text=result.get("text", ""),
                word_count=len(result.get("text", "").split()),
            )
            
            if segments:
                transcript.duration_seconds = segments[-1].end_time
            
            return TranscriptionResult(
                success=True,
                transcript=transcript,
                duration_seconds=transcript.duration_seconds,
                language=transcript.language,
                raw_response=result,
            )
            
        except Exception as e:
            logger.exception(f"Local Whisper transcription failed: {e}")
            return TranscriptionResult(
                success=False,
                error=str(e),
            )


class Transcriber:
    """
    Main transcriber class that wraps different providers.
    
    Use this as the main entry point for transcription.
    """
    
    def __init__(
        self,
        provider: TranscriptionProvider = TranscriptionProvider.WHISPER,
        **kwargs
    ):
        """
        Initialize transcriber with specified provider.
        
        Args:
            provider: Which transcription provider to use
            **kwargs: Provider-specific configuration
        """
        self.provider = provider
        self._transcriber = self._create_transcriber(provider, **kwargs)
    
    def _create_transcriber(
        self,
        provider: TranscriptionProvider,
        **kwargs
    ) -> BaseTranscriber:
        """Create the appropriate transcriber instance"""
        if provider == TranscriptionProvider.WHISPER:
            return WhisperTranscriber(**kwargs)
        elif provider == TranscriptionProvider.WHISPER_LOCAL:
            return LocalWhisperTranscriber(**kwargs)
        else:
            # Default to Whisper API
            return WhisperTranscriber(**kwargs)
    
    async def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        **kwargs
    ) -> TranscriptionResult:
        """
        Transcribe an audio file.
        
        Args:
            audio_path: Path to audio file
            language: Language code or None for auto-detect
            **kwargs: Additional options
            
        Returns:
            TranscriptionResult
        """
        # Validate file exists
        if not Path(audio_path).exists():
            return TranscriptionResult(
                success=False,
                error=f"Audio file not found: {audio_path}"
            )
        
        return await self._transcriber.transcribe(audio_path, language, **kwargs)
