"""
Tests for shared modules.
"""

import pytest
from dataclasses import dataclass
from datetime import datetime, date
from typing import Any, Dict, List, Optional

from shared.handlers.base import (
    BaseHandler,
    HandlerContext,
    HandlerResult,
    HandlerStatus,
)
from shared.mcp_tools.base import (
    BaseTool,
    ReadTool,
    WriteTool,
    ToolResult,
    ToolCategory,
)
from shared.analytics.models import (
    ChartType,
    ChartDataPoint,
    ChartSeries,
    WorkItemType,
    Priority,
)


class TestHandlerResult:
    """Tests for HandlerResult"""

    def test_success_result(self):
        """Test creating success result"""
        result = HandlerResult.success({"data": "value"}, message="Done")
        
        assert result.status == HandlerStatus.SUCCESS
        assert result.data == {"data": "value"}
        assert result.message == "Done"
        assert result.is_success is True
        assert result.is_failed is False

    def test_failure_result(self):
        """Test creating failure result"""
        result = HandlerResult.failure("Something went wrong", errors=["Error 1"])
        
        assert result.status == HandlerStatus.FAILED
        assert result.message == "Something went wrong"
        assert "Error 1" in result.errors
        assert result.is_success is False
        assert result.is_failed is True

    def test_partial_result(self):
        """Test creating partial success result"""
        result = HandlerResult.partial(
            ["item1", "item2"],
            warnings=["Skipped item3"],
            message="Partial completion"
        )
        
        assert result.status == HandlerStatus.PARTIAL
        assert len(result.data) == 2
        assert len(result.warnings) == 1
        assert result.is_success is True  # Partial is still considered success


class TestHandlerContext:
    """Tests for HandlerContext"""

    def test_context_creation(self):
        """Test creating handler context"""
        context = HandlerContext(
            user_id="user_123",
            project_id="project_456",
        )
        
        assert context.user_id == "user_123"
        assert context.project_id == "project_456"
        assert context.locale == "en-US"

    def test_context_with_project(self):
        """Test creating new context with project"""
        original = HandlerContext(user_id="user_123")
        new_context = original.with_project("new_project")
        
        assert new_context.project_id == "new_project"
        assert new_context.user_id == "user_123"
        assert original.project_id is None  # Original unchanged


class TestToolResult:
    """Tests for ToolResult"""

    def test_ok_result(self):
        """Test creating OK result"""
        result = ToolResult.ok({"items": [1, 2, 3]}, count=3)
        
        assert result.success is True
        assert result.data == {"items": [1, 2, 3]}
        assert result.metadata["count"] == 3
        assert result.error is None

    def test_fail_result(self):
        """Test creating fail result"""
        result = ToolResult.fail("Not found")
        
        assert result.success is False
        assert result.error == "Not found"
        assert result.data is None

    def test_to_mcp_response_success(self):
        """Test converting to MCP response format"""
        result = ToolResult.ok("Hello world")
        response = result.to_mcp_response()
        
        assert len(response) == 1
        assert response[0]["type"] == "text"
        assert "Hello world" in response[0]["text"]

    def test_to_mcp_response_error(self):
        """Test converting error to MCP response"""
        result = ToolResult.fail("Something failed")
        response = result.to_mcp_response()
        
        assert "Error:" in response[0]["text"]
        assert "Something failed" in response[0]["text"]


class TestAnalyticsModels:
    """Tests for shared analytics models"""

    def test_chart_types_include_meeting(self):
        """Test that meeting chart types are available"""
        assert ChartType.MEETING_DURATION is not None
        assert ChartType.MEETING_FREQUENCY is not None
        assert ChartType.PARTICIPANT_ENGAGEMENT is not None

    def test_work_item_types_include_meeting(self):
        """Test that meeting work item types are available"""
        assert WorkItemType.ACTION_ITEM is not None
        assert WorkItemType.DECISION is not None
        assert WorkItemType.FOLLOW_UP is not None

    def test_chart_data_point(self):
        """Test ChartDataPoint model"""
        point = ChartDataPoint(
            label="2024-01-01",
            value=42.0,
            color="#FF5733",
        )
        
        assert point.label == "2024-01-01"
        assert point.value == 42.0
        assert point.color == "#FF5733"

    def test_chart_series(self):
        """Test ChartSeries model"""
        series = ChartSeries(
            label="Task Count",
            data=[
                ChartDataPoint(label="Week 1", value=10),
                ChartDataPoint(label="Week 2", value=15),
            ],
        )
        
        assert series.label == "Task Count"
        assert len(series.data) == 2

    def test_priority_enum(self):
        """Test Priority enum values"""
        assert Priority.CRITICAL.value == "critical"
        assert Priority.HIGH.value == "high"
        assert Priority.MEDIUM.value == "medium"
        assert Priority.LOW.value == "low"
