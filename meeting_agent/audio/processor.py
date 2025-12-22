"""
Audio processor for meeting recordings.

Handles audio file processing, format conversion, and
preparation for transcription.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AudioInfo:
    """Information about an audio file"""
    path: str
    format: str
    duration_seconds: float
    sample_rate: int
    channels: int
    file_size_bytes: int
    bitrate: Optional[int] = None


class AudioProcessor:
    """
    Processes audio files for transcription.
    
    Supports common audio formats and can convert to
    formats required by transcription services.
    """
    
    SUPPORTED_FORMATS = {
        "mp3", "wav", "m4a", "ogg", "flac", 
        "webm", "mp4", "mpeg", "mpga"
    }
    
    def __init__(self, work_dir: str = "./tmp/audio"):
        """
        Initialize processor.
        
        Args:
            work_dir: Directory for temporary files
        """
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
    
    def validate_file(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate an audio file.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        path = Path(file_path)
        
        if not path.exists():
            return False, f"File not found: {file_path}"
        
        if not path.is_file():
            return False, f"Not a file: {file_path}"
        
        ext = path.suffix.lower().lstrip(".")
        if ext not in self.SUPPORTED_FORMATS:
            return False, f"Unsupported format: {ext}. Supported: {self.SUPPORTED_FORMATS}"
        
        return True, None
    
    def get_audio_info(self, file_path: str) -> Optional[AudioInfo]:
        """
        Get information about an audio file.
        
        Uses ffprobe if available, otherwise falls back to basic info.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            AudioInfo or None if failed
        """
        path = Path(file_path)
        
        if not path.exists():
            return None
        
        ext = path.suffix.lower().lstrip(".")
        file_size = path.stat().st_size
        
        # Try to use ffprobe for detailed info
        try:
            import subprocess
            import json
            
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "quiet",
                    "-print_format", "json",
                    "-show_format",
                    "-show_streams",
                    str(path)
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                format_info = data.get("format", {})
                streams = data.get("streams", [])
                
                # Find audio stream
                audio_stream = next(
                    (s for s in streams if s.get("codec_type") == "audio"),
                    {}
                )
                
                return AudioInfo(
                    path=str(path),
                    format=ext,
                    duration_seconds=float(format_info.get("duration", 0)),
                    sample_rate=int(audio_stream.get("sample_rate", 44100)),
                    channels=int(audio_stream.get("channels", 2)),
                    file_size_bytes=file_size,
                    bitrate=int(format_info.get("bit_rate", 0)) if format_info.get("bit_rate") else None,
                )
                
        except Exception as e:
            logger.warning(f"ffprobe failed, using basic info: {e}")
        
        # Fall back to basic info
        return AudioInfo(
            path=str(path),
            format=ext,
            duration_seconds=0,  # Unknown without ffprobe
            sample_rate=44100,   # Assume standard
            channels=2,          # Assume stereo
            file_size_bytes=file_size,
        )
    
    async def prepare_for_transcription(
        self,
        file_path: str,
        target_format: str = "mp3",
        target_sample_rate: int = 16000,
    ) -> str:
        """
        Prepare audio file for transcription.
        
        Converts to the format and sample rate expected by
        the transcription service.
        
        Args:
            file_path: Path to source audio
            target_format: Output format
            target_sample_rate: Target sample rate (16kHz is common for speech)
            
        Returns:
            Path to prepared audio file
        """
        path = Path(file_path)
        
        # If already in target format with good sample rate, return as-is
        if path.suffix.lower().lstrip(".") == target_format:
            return str(path)
        
        # Convert using ffmpeg
        output_path = self.work_dir / f"{path.stem}_prepared.{target_format}"
        
        try:
            import subprocess
            
            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output
                "-i", str(path),
                "-ar", str(target_sample_rate),
                "-ac", "1",  # Mono for speech
                "-q:a", "2",  # Quality
                str(output_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 min timeout
            )
            
            if result.returncode != 0:
                logger.error(f"ffmpeg conversion failed: {result.stderr}")
                return str(path)  # Return original on failure
            
            return str(output_path)
            
        except FileNotFoundError:
            logger.warning("ffmpeg not found, returning original file")
            return str(path)
        except Exception as e:
            logger.error(f"Audio conversion failed: {e}")
            return str(path)
    
    def split_audio(
        self,
        file_path: str,
        chunk_duration_seconds: int = 600,  # 10 minutes
    ) -> list[str]:
        """
        Split audio into chunks for processing.
        
        Useful for very long recordings that exceed API limits.
        
        Args:
            file_path: Path to audio file
            chunk_duration_seconds: Max duration per chunk
            
        Returns:
            List of paths to chunk files
        """
        info = self.get_audio_info(file_path)
        if not info:
            return [file_path]
        
        # If short enough, no splitting needed
        if info.duration_seconds <= chunk_duration_seconds:
            return [file_path]
        
        # Calculate number of chunks
        num_chunks = int(info.duration_seconds / chunk_duration_seconds) + 1
        
        chunks = []
        path = Path(file_path)
        
        try:
            import subprocess
            
            for i in range(num_chunks):
                start = i * chunk_duration_seconds
                chunk_path = self.work_dir / f"{path.stem}_chunk{i:03d}{path.suffix}"
                
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i", str(path),
                    "-ss", str(start),
                    "-t", str(chunk_duration_seconds),
                    "-c", "copy",
                    str(chunk_path)
                ]
                
                result = subprocess.run(cmd, capture_output=True, timeout=120)
                
                if result.returncode == 0 and chunk_path.exists():
                    chunks.append(str(chunk_path))
            
            return chunks if chunks else [file_path]
            
        except Exception as e:
            logger.error(f"Audio splitting failed: {e}")
            return [file_path]
    
    def cleanup(self) -> None:
        """Clean up temporary files"""
        import shutil
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir)
            self.work_dir.mkdir(parents=True, exist_ok=True)
