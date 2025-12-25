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
        enforce_limit: bool = True,
    ) -> str:
        """
        Prepare audio file for transcription.
        
        Converts to the format and sample rate expected by
        the transcription service.
        
        Args:
            file_path: Path to source audio
            target_format: Output format
            target_sample_rate: Target sample rate (16kHz is common for speech)
            enforce_limit: Whether to raise error if result > 25MB
            
        Returns:
            Path to prepared audio file
        """
        path = Path(file_path)
        
        # Output path
        output_path = self.work_dir / f"{path.stem}_prepared.{target_format}"

        # If already in target format with good sample rate, return as-is
        if path.suffix.lower().lstrip(".") == target_format:
            return str(path)
        
        # Convert using ffmpeg with aggressive compression for Whisper
        # 32k-64k bitrate is usually sufficient for speech to text
        
        try:
            import subprocess
            
            # Use fixed bitrate 64k instead of q:a 2 (which can be large)
            common_args = [
                "-ar", str(target_sample_rate),
                "-ac", "1",  # Mono
                "-b:a", "64k", # Fixed chunks, small size
                "-map", "a",   # specific for audio
            ]
            
            cmd = [
                "ffmpeg",
                "-y",
                "-i", str(path),
                *common_args,
                str(output_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600 # Increase timeout to 10 min
            )
            
            if result.returncode != 0:
                logger.warning(f"Standard ffmpeg conversion failed: {result.stderr}")
                
                # Recovery attempt
                logger.info("Attempting recovery with ignore_err...")
                cmd_recovery = [
                    "ffmpeg",
                    "-y",
                    "-err_detect", "ignore_err",
                    "-i", str(path),
                    *common_args,
                    str(output_path)
                ]
                
                result_recovery = subprocess.run(
                    cmd_recovery,
                    capture_output=True,
                    text=True,
                    timeout=600
                )
                
                if result_recovery.returncode != 0:
                    logger.warning(f"Recovery (Tier 2) failed: {result_recovery.stderr}")
                    
                    # Tier 3: Try extracting raw audio stream (bypass container issues)
                    # Often works for 'moov atom not found' if stream is intact
                    logger.info("Attempting Tier 3 recovery (raw stream extraction)...")
                    try:
                        temp_aac = self.work_dir / f"{path.stem}_temp.aac"
                        cmd_extract = [
                            "ffmpeg",
                            "-y",
                            "-i", str(path),
                            "-vn", # No video
                            "-acodec", "copy", # Stream copy
                            str(temp_aac)
                        ]
                        subprocess.run(cmd_extract, capture_output=True, text=True, timeout=300)
                        
                        if temp_aac.exists() and temp_aac.stat().st_size > 0:
                            logger.info("Tier 3 extraction successful, re-encoding to target...")
                            # Now re-encode the properly extracted stream
                            cmd_final = [
                                "ffmpeg",
                                "-y",
                                "-i", str(temp_aac),
                                *common_args,
                                str(output_path)
                            ]
                            # If this fails, it falls through to Tier 4
                            result_final = subprocess.run(cmd_final, capture_output=True, text=True, timeout=300)
                            
                            # Cleanup temp
                            try: temp_aac.unlink()
                            except: pass
                                
                            if result_final.returncode == 0:
                                return str(output_path)
                    except Exception as ex:
                        logger.error(f"Tier 3 failed: {ex}")

                    # Tier 4: Force raw ADTS AAC interpretion (Hail Mary)
                    # Instead of re-encoding (which might fail), we WRAP it in a clean m4a container
                    # forcing header generation. This allows downstream tools/splitters to work.
                    logger.info("Attempting Tier 4 recovery (force aac demuxer + wrap)...")
                    try:
                        temp_aac_raw = self.work_dir / f"{path.stem}_raw.aac"
                        cmd_force = [
                            "ffmpeg",
                            "-y",
                            "-f", "aac", # Force AAC demuxer
                            "-i", str(path),
                            "-c:a", "copy",
                            str(temp_aac_raw)
                        ]
                        result_force = subprocess.run(cmd_force, capture_output=True, text=True, timeout=300)
                        
                        if result_force.returncode == 0 and temp_aac_raw.exists() and temp_aac_raw.stat().st_size > 0:
                            logger.info("Tier 4 successful, wrapping in M4A container...")
                            
                            # Wrap in m4a so it's a valid file for splitting/transcribing
                            safe_m4a = self.work_dir / f"{path.stem}_recovered.m4a"
                            cmd_wrap = [
                                "ffmpeg",
                                "-y",
                                "-i", str(temp_aac_raw),
                                "-c:a", "copy",
                                "-bsf:a", "aac_adtstoasc", # Critical for AAC -> MP4
                                str(safe_m4a)
                            ]
                            result_wrap = subprocess.run(cmd_wrap, capture_output=True, text=True, timeout=300)
                            
                            try: temp_aac_raw.unlink()
                            except: pass
                                
                            if result_wrap.returncode == 0:
                                # We return the M4A. It might be large, but it's valid.
                                # Check limit ONLY if enforce_limit is True
                                if enforce_limit:
                                    size = safe_m4a.stat().st_size
                                    if size > 25 * 1024 * 1024:
                                         # If too big, we still return it but warn? 
                                         # No, raising ValueError as requested, but caller can disable this.
                                         raise ValueError(f"Recovered file valid but too large ({size/1024/1024:.2f}MB). Needs splitting.")
                                return str(safe_m4a)
                                
                    except Exception as ex:
                        logger.error(f"Tier 4 failed: {ex}")

                    # Final check: If original file is too big (25MB limit), we cannot return it
                    original_size = path.stat().st_size
                    if enforce_limit and original_size > 25 * 1024 * 1024: # 25MB
                         raise ValueError(f"Audio processing failed (all tiers) and original file ({original_size/1024/1024:.2f}MB) exceeds OpenAI 25MB limit.")
                    
                    return str(path)  # Return original if small enough
                
                logger.info("Recovery (Tier 2) successful")
                return str(output_path)
            
            return str(output_path)
            
        except FileNotFoundError:
            logger.warning("ffmpeg not found, returning original file")
             # Final check
            original_size = path.stat().st_size
            if enforce_limit and original_size > 25 * 1024 * 1024:
                raise ValueError(f"ffmpeg not found and file ({original_size/1024/1024:.2f}MB) exceeds OpenAI 25MB limit.")
            return str(path)
        except Exception as e:
            logger.error(f"Audio conversion failed: {e}")
            original_size = path.stat().st_size
            if enforce_limit and original_size > 25 * 1024 * 1024:
                raise ValueError(f"Processing failed: {e}. File ({original_size/1024/1024:.2f}MB) exceeds limit.")
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
