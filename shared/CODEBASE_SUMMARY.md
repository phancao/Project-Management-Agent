# Shared Library - Codebase Summary

## Overview
Reusable components shared between PM Agent and Meeting Notes Agent.

## Purpose
Provides common base classes, utilities, and patterns to avoid code duplication across agents.

---

## Module Structure

```
shared/
├── analytics/          # Chart models, calculators, adapters
├── handlers/           # Base handler pattern
├── mcp_tools/          # MCP tool base classes
├── prompts/            # Prompt utilities
├── config/             # Shared configuration
└── database/           # Database utilities
```

---

## Key Components

### analytics/
- `models.py` - ChartType, ChartDataPoint, ChartSeries, WorkItemType, Priority
- `base.py` - BaseCalculator, WorkItemCalculator, TimeSeriesCalculator
- `adapters/` - BaseAnalyticsAdapter, CachingAdapter

### handlers/
- `base.py` - BaseHandler, HandlerContext, HandlerResult, HandlerStatus
- `pm_handler.py` - BasePMHandler with create_task, assign_task, list_users

### mcp_tools/
- `base.py` - BaseTool, ReadTool, WriteTool, AnalyticsTool, ToolResult
- `decorators.py` - @mcp_tool, @require_project, @cache_result, @validate_schema

### prompts/
- `utils.py` - load_prompt, render_template, combine_prompts
- `common/system.md` - Shared system prompt template

---

## Usage

```python
from shared.handlers import BaseHandler, HandlerContext, HandlerResult
from shared.analytics.models import ChartType, ChartDataPoint
from shared.mcp_tools import BaseTool, mcp_tool

class MyHandler(BaseHandler):
    async def execute(self, context: HandlerContext, **kwargs) -> HandlerResult:
        # Implementation
        return HandlerResult.success(data)
```

---

## Dependencies
- pydantic
- No external agent dependencies (base package)
