# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""PM Tools - Stub for testing LangGraph features.

This file is a minimal stub to allow the server to start.
The full PM tools implementation will be restored later.
"""

import logging
from typing import List

logger = logging.getLogger(__name__)

# Global PM handler (will be set by ConversationFlowManager)
_pm_handler = None


def set_pm_handler(handler):
    """Set the PM handler instance for tools to use"""
    global _pm_handler
    _pm_handler = handler
    logger.debug(f"PM handler set: {handler is not None}")


def get_pm_tools() -> List:
    """Get list of all PM tools.
    
    Returns empty list for now since PM tools are not fully implemented.
    """
    return []
