"""
Integration tests for MCP Meeting Server tools.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Import ORM models for mocking
from database.orm_models import (
    Meeting,
    MeetingSummary,
    MeetingActionItem,
    MeetingParticipant
)


class MockMCPServer:
    """Mock MCP Server for testing"""
    
    def __init__(self):
        self.config = MagicMock()
        self.config.upload_dir = "/tmp/test_uploads"
        self.db_session = MagicMock()
        
    def get_upload_dir(self):
        from pathlib import Path
        return Path(self.config.upload_dir)
    
    def get_meeting_handler(self):
        handler = MagicMock()
        handler.execute = AsyncMock()
        handler.process_from_text = AsyncMock()
        return handler
        
    def get_db_session(self):
        return self.db_session


class TestMCPMeetingTools:
    """Tests for MCP meeting tools"""

    @pytest.fixture
    def mock_server(self):
        return MockMCPServer()

    @pytest.mark.asyncio
    async def test_analyze_transcript_tool(self, mock_server):
        """Test the analyze_transcript tool"""
        from mcp_meeting_server.tools import _handle_analyze_transcript
        from shared.handlers import HandlerResult
        from meeting_agent.models import MeetingSummary as PydanticSummary
        from meeting_agent.models import ActionItem, ActionItemPriority
        
        # Setup mock handler result (Pydantic model)
        mock_pydantic_summary = PydanticSummary(
            meeting_id="mtg_test",
            executive_summary="Test summary",
            key_points=["Point 1"],
            action_items=[
                ActionItem(
                    id="ai_1",
                    meeting_id="mtg_test",
                    description="Test action",
                    priority=ActionItemPriority.HIGH,
                )
            ],
        )
        
        mock_result = HandlerResult.success(mock_pydantic_summary, meeting_id="mtg_test")
        mock_server.get_meeting_handler().process_from_text = AsyncMock(
            return_value=mock_result
        )
        
        # Call tool
        result = await _handle_analyze_transcript(mock_server, {
            "transcript": "Alice: We need to finish the report.\nBob: I'll handle it.",
            "title": "Quick Sync",
            "participants": ["Alice", "Bob"],
        })
        
        # Verify DB calls
        # Should add Meeting, Participants, Transcript, Summary, ActionItems
        assert mock_server.db_session.add.call_count >= 1
        assert mock_server.db_session.commit.call_count >= 1
        
        # Verify result
        assert len(result) == 1
        assert result[0]["type"] == "text"
        assert "analyzed" in result[0]["text"].lower() or "summary" in result[0]["text"].lower()

    @pytest.mark.asyncio
    async def test_list_meetings_tool(self, mock_server):
        """Test the list_meetings tool"""
        from mcp_meeting_server.tools import _handle_list_meetings
        
        # Mock DB query
        mock_query = mock_server.db_session.query.return_value
        mock_query.order_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        
        mock_meetings = [
            Meeting(id="mtg_001", title="Meeting 1", status="completed"),
            Meeting(id="mtg_002", title="Meeting 2", status="pending")
        ]
        mock_query.limit.return_value.all.return_value = mock_meetings
        
        # Call tool
        result = await _handle_list_meetings(mock_server, {"status": "all"})
        
        # Verify
        assert len(result) == 1
        assert "Meeting 1" in result[0]["text"]
        assert "Meeting 2" in result[0]["text"]

    @pytest.mark.asyncio
    async def test_list_action_items_tool(self, mock_server):
        """Test the list_action_items tool"""
        from mcp_meeting_server.tools import _handle_list_action_items
        
        # Mock DB query
        mock_query = mock_server.db_session.query.return_value
        mock_query.filter.return_value = mock_query
        
        mock_items = [
            MeetingActionItem(
                description="Complete documentation",
                assignee_name="Alice",
                status="pending"
            )
        ]
        mock_query.all.return_value = mock_items
        
        # Call tool
        result = await _handle_list_action_items(mock_server, {
            "meeting_id": "mtg_test",
        })
        
        # Verify
        assert len(result) == 1
        assert "Complete documentation" in result[0]["text"]
        assert "Alice" in result[0]["text"]


class TestMCPServerCreation:
    """Tests for MCP server initialization"""

    def test_server_creation(self):
        """Test creating an MCP meeting server"""
        from mcp_meeting_server import MeetingMCPServer
        from mcp_meeting_server.config import MeetingServerConfig
        
        config = MeetingServerConfig(
            transport="http",
            port=8082,
        )
        
        # Patch recursive mkdir to avoid permission errors
        with patch("pathlib.Path.mkdir"):
            server = MeetingMCPServer(config=config)
        
        assert server.config.transport == "http"
        assert server.config.port == 8082

    def test_config_from_env(self):
        """Test loading config from environment"""
        import os
        from mcp_meeting_server.config import MeetingServerConfig
        
        # Set env vars
        os.environ["MEETING_SERVER_PORT"] = "9999"
        os.environ["MEETING_SERVER_TRANSPORT"] = "sse"
        
        config = MeetingServerConfig.from_env()
        
        assert config.port == 9999
        assert config.transport == "sse"
        
        # Cleanup
        del os.environ["MEETING_SERVER_PORT"]
        del os.environ["MEETING_SERVER_TRANSPORT"]
