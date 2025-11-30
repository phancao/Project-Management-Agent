# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
Pytest configuration and fixtures for all tests.

This file ensures the project root is in the Python path
so that imports work correctly for all test modules.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import pytest for fixtures
import pytest


@pytest.fixture
def project_root_path():
    """Return the project root path."""
    return project_root


