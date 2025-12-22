"""
Shared Handlers Package

This package provides base handler classes and common handler utilities
that can be used by both PM Agent and Meeting Notes Agent.

Handlers are responsible for:
- Executing complex operations (report generation, sprint planning, etc.)
- Coordinating between multiple services
- Providing business logic abstraction
"""

from shared.handlers.base import (
    BaseHandler,
    HandlerContext,
    HandlerResult,
    HandlerStatus,
)

__all__ = [
    'BaseHandler',
    'HandlerContext',
    'HandlerResult',
    'HandlerStatus',
]
