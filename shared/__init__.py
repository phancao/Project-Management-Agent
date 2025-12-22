"""
Shared Modules Package

This package contains modules that are shared between multiple agents:
- PM Agent (Project Management)
- Meeting Notes Agent
- Future agents

Shared modules include:
- analytics: Chart and metrics models, calculators, adapters
- config: Shared configuration models
- database: Shared database models and utilities
"""

from shared.analytics import (
    ChartDataPoint,
    ChartSeries,
    ChartResponse,
    ChartType,
    TaskStatus,
    WorkItemType,
    Priority,
    WorkItem,
    SprintData,
)

__all__ = [
    # Analytics exports
    'ChartDataPoint',
    'ChartSeries',
    'ChartResponse',
    'ChartType',
    'TaskStatus',
    'WorkItemType',
    'Priority',
    'WorkItem',
    'SprintData',
]
