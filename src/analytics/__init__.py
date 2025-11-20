"""
Analytics module for project management charts and metrics.

This module provides server-side analytics and chart generation that can be
consumed by the frontend UI, AI agents, and external systems via REST API.
"""

from src.analytics.models import (
    ChartDataPoint,
    ChartSeries,
    ChartResponse,
    ChartType,
    SprintData,
    TaskTransition,
    WorkItem
)
from src.analytics.service import AnalyticsService

__all__ = [
    'ChartDataPoint',
    'ChartSeries', 
    'ChartResponse',
    'ChartType',
    'SprintData',
    'TaskTransition',
    'WorkItem',
    'AnalyticsService'
]
















