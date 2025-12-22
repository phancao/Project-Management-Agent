"""
Tests for Meeting Agent audio processing.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import tempfile
import os

from meeting_agent.audio.processor import AudioProcessor, AudioInfo
from meeting_agent.audio.transcriber import (
    Transcriber,
    TranscriptionResult,
    WhisperTranscriber,
)
from meeting_agent.config import TranscriptionProvider


class TestAudioProcessor:
    """Tests for AudioProcessor"""

    def setup_method(self):
        """Setup for each test"""
        self.temp_dir = tempfile.mkdtemp()
        self.processor = AudioProcessor(work_dir=self.temp_dir)

    def teardown_method(self):
        """Cleanup after each test"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_validate_nonexistent_file(self):
        """Test validation fails for missing file"""
        valid, error = self.processor.validate_file("/nonexistent/file.mp3")
        
        assert valid is False
        assert "not found" in error.lower()

    def test_validate_unsupported_format(self):
        """Test validation fails for unsupported format"""
        # Create a temp file with unsupported extension
        temp_file = os.path.join(self.temp_dir, "test.xyz")
        Path(temp_file).touch()
        
        valid, error = self.processor.validate_file(temp_file)
        
        assert valid is False
        assert "unsupported" in error.lower()

    def test_validate_supported_format(self):
        """Test validation succeeds for supported format"""
        temp_file = os.path.join(self.temp_dir, "test.mp3")
        Path(temp_file).touch()
        
        valid, error = self.processor.validate_file(temp_file)
        
        assert valid is True
        assert error is None

    def test_get_audio_info_basic(self):
        """Test getting basic audio info"""
        temp_file = os.path.join(self.temp_dir, "test.wav")
        Path(temp_file).write_bytes(b"dummy audio content")
        
        info = self.processor.get_audio_info(temp_file)
        
        assert info is not None
        assert info.format == "wav"
        assert info.file_size_bytes > 0

    def test_supported_formats(self):
        """Test supported format list"""
        expected = {"mp3", "wav", "m4a", "ogg", "flac", "webm", "mp4", "mpeg", "mpga"}
        assert self.processor.SUPPORTED_FORMATS == expected


class TestTranscriber:
    """Tests for Transcriber"""

    def test_transcriber_creation(self):
        """Test creating transcriber with default provider"""
        transcriber = Transcriber()
        assert transcriber.provider == TranscriptionProvider.WHISPER

    def test_transcriber_with_local_whisper(self):
        """Test creating transcriber with local whisper"""
        transcriber = Transcriber(provider=TranscriptionProvider.WHISPER_LOCAL)
        assert transcriber.provider == TranscriptionProvider.WHISPER_LOCAL

    @pytest.mark.asyncio
    async def test_transcribe_missing_file(self):
        """Test transcription fails for missing file"""
        transcriber = Transcriber()
        
        result = await transcriber.transcribe("/nonexistent/audio.mp3")
        
        assert result.success is False
        assert "not found" in result.error.lower()


class TestWhisperTranscriber:
    """Tests for WhisperTranscriber"""

    def test_whisper_transcriber_init(self):
        """Test WhisperTranscriber initialization"""
        transcriber = WhisperTranscriber(api_key="test-key", model="whisper-1")
        
        assert transcriber.api_key == "test-key"
        assert transcriber.model == "whisper-1"

    @pytest.mark.asyncio
    async def test_whisper_transcribe_without_api_key(self):
        """Test transcription fails gracefully without API key"""
        # Temporarily unset the API key
        old_key = os.environ.pop("OPENAI_API_KEY", None)
        
        try:
            transcriber = WhisperTranscriber(api_key=None)
            # Note: The actual call would fail, this just tests initialization
            assert transcriber.api_key is None
        finally:
            if old_key:
                os.environ["OPENAI_API_KEY"] = old_key


class TestTranscriptionResult:
    """Tests for TranscriptionResult"""

    def test_successful_result(self):
        """Test creating successful result"""
        from meeting_agent.models import Transcript
        
        transcript = Transcript(
            meeting_id="test",
            language="en",
            full_text="Hello world",
            segments=[],
        )
        
        result = TranscriptionResult(
            success=True,
            transcript=transcript,
            language="en",
            duration_seconds=60.0,
        )
        
        assert result.success is True
        assert result.transcript is not None
        assert result.error is None

    def test_failed_result(self):
        """Test creating failed result"""
        result = TranscriptionResult(
            success=False,
            error="API error",
        )
        
        assert result.success is False
        assert result.transcript is None
        assert result.error == "API error"
