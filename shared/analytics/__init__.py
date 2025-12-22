"""
Shared Analytics Module

This module provides shared analytics models and base classes that can be used
by both the PM Agent and Meeting Notes Agent (and any future agents).

The module includes:
- Data models for charts and analytics (ChartResponse, SprintData, etc.)
- Base classes for analytics calculators
- Adapters for integrating with different data sources
"""

from shared.analytics.models import (
    ChartDataPoint,
    ChartSeries,
    ChartResponse,
    ChartType,
    TaskStatus,
    WorkItemType,
    Priority,
    WorkItem,
    TaskTransition,
    SprintData,
    VelocityDataPoint,
    CycleTimeDataPoint,
    DistributionData,
    TrendDataPoint,
    SprintReport,
)

__all__ = [
    # Chart models
    'ChartDataPoint',
    'ChartSeries',
    'ChartResponse',
    'ChartType',
    # Domain models
    'TaskStatus',
    'WorkItemType',
    'Priority',
    'WorkItem',
    'TaskTransition',
    'SprintData',
    # Analytics-specific models
    'VelocityDataPoint',
    'CycleTimeDataPoint',
    'DistributionData',
    'TrendDataPoint',
    'SprintReport',
]
