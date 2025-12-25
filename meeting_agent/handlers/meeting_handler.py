"""
Main meeting handler.

Orchestrates the complete meeting processing pipeline:
audio processing → transcription → analysis → PM integration.
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from shared.handlers.base import BaseHandler, HandlerContext, HandlerResult
from meeting_agent.config import MeetingAgentConfig
from meeting_agent.models import (
    Meeting,
    MeetingStatus,
    MeetingMetadata,
    Transcript,
    Participant,
    MeetingSummary,
    ActionItem,
)
from meeting_agent.audio import AudioProcessor, Transcriber, TranscriptionResult
from meeting_agent.analysis import MeetingSummarizer, ActionExtractor
from meeting_agent.database import MeetingRepository
from meeting_agent.integrations import MeetingPMIntegration

logger = logging.getLogger(__name__)


class MeetingHandler(BaseHandler[MeetingSummary]):
    """
    Main handler for processing meetings.
    
    Coordinates the entire pipeline from audio upload
    through transcription, analysis, and PM task creation.
    """
    
    @property
    def name(self) -> str:
        return "meeting_handler"
    
    def __init__(
        self,
        config: Optional[MeetingAgentConfig] = None,
        pm_handler: Optional[Any] = None,  # BasePMHandler
        database_url: Optional[str] = None,
        provider_manager: Optional[Any] = None,
    ):
        """
        Initialize meeting handler.
        
        Args:
            config: Meeting agent configuration
            pm_handler: Optional PM handler for task creation
            database_url: Database URL for persistence
            provider_manager: Optional ProviderManager for fetching AI keys
        """
        self.config = config or MeetingAgentConfig()
        self.pm_handler = pm_handler
        self.provider_manager = provider_manager
        
        # Initialize components
        self.audio_processor = AudioProcessor(work_dir=self.config.upload_dir + "/tmp")
        self.transcriber = Transcriber(
            provider=self.config.transcription_provider,
            model=self.config.whisper_model,
        )
        self.summarizer = MeetingSummarizer()
        self.action_extractor = ActionExtractor()
        
        # Database persistence
        db_url = database_url or "sqlite:///./data/meetings.db"
        self.repository = MeetingRepository(db_url)
        
        # PM Integration
        self.pm_integration = MeetingPMIntegration()
    
    async def execute(
        self,
        context: HandlerContext,
        audio_path: Optional[str] = None,
        meeting_title: str = "Untitled Meeting",
        participants: Optional[List[str]] = None,
        project_id: Optional[str] = None,
        **kwargs
    ) -> HandlerResult[MeetingSummary]:
        """
        Process a meeting from audio file.
        
        Args:
            context: Handler context
            audio_path: Path to audio/video file
            meeting_title: Title for the meeting
            participants: List of participant names
            project_id: PM project to link tasks to
            
        Returns:
            HandlerResult with MeetingSummary
        """
        if not audio_path:
            return HandlerResult.failure("audio_path is required")
        
        # Create meeting object
        meeting = Meeting(
            id=f"mtg_{uuid.uuid4().hex[:12]}",
            title=meeting_title,
            status=MeetingStatus.PENDING,
            participants=[
                Participant(name=name) for name in (participants or [])
            ],
            project_id=project_id or context.project_id,
            metadata=MeetingMetadata(file_path=audio_path),
        )
        
        try:
            # Step 1: Validate and prepare audio
            logger.info(f"Processing meeting: {meeting.id}")
            meeting.status = MeetingStatus.TRANSCRIBING
            
            valid, error = self.audio_processor.validate_file(audio_path)
            if not valid:
                return HandlerResult.failure(f"Invalid audio file: {error}")
            
            audio_info = self.audio_processor.get_audio_info(audio_path)
            if audio_info:
                meeting.metadata.file_size_bytes = audio_info.file_size_bytes
                meeting.metadata.audio_format = audio_info.format
            
            # Prepare audio for transcription with soft limit
            prepared_path = await self.audio_processor.prepare_for_transcription(
                audio_path,
                enforce_limit=False 
            )
            
            # Resolve OpenAI API Key (STRICT MODE: DB Only)
            api_key = None
            if self.provider_manager:
                try:
                    # Look for openai provider in AI Providers (Main DB)
                    if hasattr(self.provider_manager, 'get_ai_provider'):
                        openai_data = self.provider_manager.get_ai_provider('openai')
                        if openai_data and openai_data.get('api_key'):
                            api_key = openai_data['api_key']
                            logger.info("Using OpenAI API key from ProviderManager (AI Provider)")

                    # Fallback: Look in PM Providers (MCP DB) if not found in AI Providers
                    if not api_key:
                        providers = self.provider_manager.get_active_providers()
                        openai_provider = next((p for p in providers if p.provider_type == 'openai'), None)
                        if openai_provider and openai_provider.api_key:
                            api_key = openai_provider.api_key
                            logger.info("Using OpenAI API key from ProviderManager (PM Provider)")
                except Exception as e:
                    logger.warning(f"Failed to fetch OpenAI key from provider manager: {e}")
            
            if not api_key:
                raise ValueError("OpenAI provider not configured. Please add the 'openai' provider in Settings > AI Providers.")

            # Step 2: Transcribe (with Chunking Support)
            logger.info(f"Transcribing: {prepared_path}")
            
            # Update transcriber key if we found one
            if api_key and hasattr(self.transcriber, '_transcriber'):
                 if hasattr(self.transcriber._transcriber, 'api_key'):
                     self.transcriber._transcriber.api_key = api_key
            
            # Check file size
            file_size = Path(prepared_path).stat().st_size
            limit_bytes = 25 * 1024 * 1024 # 25MB
            
            if file_size > limit_bytes:
                logger.info(f"File size ({file_size/1024/1024:.2f}MB) exceeds limit, splitting into chunks...")
                chunks = self.audio_processor.split_audio(prepared_path)
                logger.info(f"Split into {len(chunks)} chunks")
                
                full_text_parts = []
                all_segments = []
                
                for i, chunk_path in enumerate(chunks):
                    logger.info(f"Transcribing chunk {i+1}/{len(chunks)}: {chunk_path}")
                    chunk_result = await self.transcriber.transcribe(
                        chunk_path,
                        language=self.config.whisper_language,
                    )
                    
                    if not chunk_result.success:
                        logger.error(f"Chunk {i+1} failed: {chunk_result.error}")
                        # Continue with what we have? Or fail?
                        # Let's fail for now to ensure quality
                        return HandlerResult.failure(f"Transcription failed on chunk {i+1}: {chunk_result.error}")
                        
                    if chunk_result.transcript:
                        full_text_parts.append(chunk_result.transcript.full_text)
                        # Adjust segment timestamps? For now simple append
                        all_segments.extend(chunk_result.transcript.segments)
                
                # Merge transcripts
                merged_text = "\n\n".join(full_text_parts)
                # Recalculate word count
                word_count = len(merged_text.split())
                
                # Create merged transcript object
                meeting.transcript = Transcript(
                    meeting_id=meeting.id,
                    full_text=merged_text,
                    word_count=word_count,
                    segments=all_segments
                )
                
                # Cleanup chunks
                try:
                    for c in chunks:
                        Path(c).unlink(missing_ok=True)
                except:
                    pass
                    
            else:
                # Single file transcription
                transcription_result = await self.transcriber.transcribe(
                    prepared_path,
                    language=self.config.whisper_language,
                )
                
                if not transcription_result.success:
                    meeting.status = MeetingStatus.FAILED
                    meeting.error_message = transcription_result.error
                    return HandlerResult.failure(
                        f"Transcription failed: {transcription_result.error}"
                    )
                
                # Attach transcript to meeting
                meeting.transcript = transcription_result.transcript
                meeting.transcript.meeting_id = meeting.id
            
            # Fetch project context
            project_context = {}
            if meeting.project_id and self.pm_integration:
                logger.info(f"Fetching context for project: {meeting.project_id}")
                ctx_result = await self.pm_integration.get_project_context(meeting.project_id)
                if ctx_result.is_success:
                    project_context = ctx_result.data
                
                # Fetch project participants
                users_result = await self.pm_integration.get_project_users(meeting.project_id)
                if users_result.is_success:
                    project_context["participants"] = users_result.data
            
            # Analyze
            logger.info(f"Analyzing meeting: {meeting.id}")
            meeting.status = MeetingStatus.ANALYZING
            
            # Pass API key to analysis tools via config or direct argument?
            # Looking at Summarizer/ActionExtractor, they use config or env.
            # We need to update them to accept key in method or init.
            # For now, let's assume we can inject it into their config if they expose it, 
            # OR we pass it in invoke. But the signature doesn't support it yet.
            # We will update Summarizer/Extractor signature separately.
            # For now, let's just stick to the plan of injecting to config logic if possible.
            # Actually, simpler to pass it to the methods.
            
            # Get summary
            summary = await self.summarizer.summarize(
                meeting, 
                project_context=project_context,
                api_key=api_key
            )
            
            # Extract action items
            action_items, decisions, follow_ups = await self.action_extractor.extract(
                meeting,
                participant_mapping=self._build_participant_mapping(meeting),
                project_context=project_context,
                api_key=api_key
            )
            
            # Add to summary
            summary.action_items = action_items
            summary.decisions = decisions
            summary.follow_ups = follow_ups
            
            # Step 4: Create PM tasks if configured
            created_tasks = []
            if self.pm_handler and meeting.project_id and action_items:
                logger.info(f"Creating {len(action_items)} tasks in PM system")
                
                if self.config.auto_create_tasks:
                    created_tasks = await self._create_pm_tasks(
                        context, meeting.project_id, action_items
                    )
            
            # Mark complete
            meeting.status = MeetingStatus.COMPLETED
            meeting.processed_at = datetime.now()
            
            # Persist to database
            try:
                self.repository.create_meeting(meeting)
                self.repository.save_transcript(meeting.id, meeting.transcript)
                self.repository.save_action_items(meeting.id, action_items)
                self.repository.save_decisions(meeting.id, decisions)
                self.repository.save_summary(meeting.id, summary)
                logger.info(f"Persisted meeting {meeting.id} to database")
            except Exception as db_err:
                logger.warning(f"Failed to persist to database: {db_err}")
            
            return HandlerResult.success(
                summary,
                message=f"Processed meeting with {len(action_items)} action items",
                meeting_id=meeting.id,
                tasks_created=len(created_tasks),
                duration_minutes=meeting.duration_minutes,
            )
            
        except Exception as e:
            logger.exception(f"Meeting processing failed: {e}")
            meeting.status = MeetingStatus.FAILED
            meeting.error_message = str(e)
            return HandlerResult.failure(f"Meeting processing failed: {str(e)}")
    
    async def validate(
        self,
        context: HandlerContext,
        audio_path: Optional[str] = None,
        **kwargs
    ) -> Optional[str]:
        """Validate inputs before processing"""
        if not audio_path:
            return "audio_path is required"
        
        if not Path(audio_path).exists():
            return f"Audio file not found: {audio_path}"
        
        return None
    
    def _build_participant_mapping(self, meeting: Meeting) -> Dict[str, str]:
        """Build mapping of participant names to PM user IDs"""
        mapping = {}
        for participant in meeting.participants:
            if participant.pm_user_id:
                mapping[participant.name] = participant.pm_user_id
        return mapping
    
    async def _create_pm_tasks(
        self,
        context: HandlerContext,
        project_id: str,
        action_items: List[ActionItem],
    ) -> List[Any]:
        """Create tasks in PM system from action items"""
        if not self.pm_handler:
            return []
        
        created = []
        for item in action_items:
            task_data = item.to_pm_task_data()
            result = await self.pm_handler.create_task(
                context, project_id, task_data
            )
            if result.is_success and result.data:
                item.pm_task_id = result.data.id
                item.pm_task_url = getattr(result.data, 'url', None)
                created.append(result.data)
        
        return created
    
    async def process_from_text(
        self,
        context: HandlerContext,
        transcript_text: str,
        meeting_title: str = "Untitled Meeting",
        participants: Optional[List[str]] = None,
        project_id: Optional[str] = None,
    ) -> HandlerResult[MeetingSummary]:
        """
        Process a meeting from raw transcript text.
        
        Use this when you already have a transcription
        and don't need audio processing.
        """
        meeting = Meeting(
            id=f"mtg_{uuid.uuid4().hex[:12]}",
            title=meeting_title,
            status=MeetingStatus.ANALYZING,
            participants=[
                Participant(name=name) for name in (participants or [])
            ],
            project_id=project_id or context.project_id,
            transcript=Transcript(
                meeting_id="",  # Will be set below
                full_text=transcript_text,
                word_count=len(transcript_text.split()),
                segments=[],
            ),
        )
        meeting.transcript.meeting_id = meeting.id
        
        try:
            # Fetch project context
            project_context = {}
            if meeting.project_id and self.pm_integration:
                ctx_result = await self.pm_integration.get_project_context(meeting.project_id)
                if ctx_result.is_success:
                    project_context = ctx_result.data

            # Analyze
            summary = await self.summarizer.summarize(meeting, project_context=project_context)
            action_items, decisions, follow_ups = await self.action_extractor.extract(
                meeting,
                project_context=project_context
            )
            
            summary.action_items = action_items
            summary.decisions = decisions
            summary.follow_ups = follow_ups
            
            meeting.status = MeetingStatus.COMPLETED
            
            return HandlerResult.success(
                summary,
                message=f"Analyzed transcript with {len(action_items)} action items",
                meeting_id=meeting.id,
            )
            
        except Exception as e:
            return HandlerResult.failure(f"Analysis failed: {str(e)}")
