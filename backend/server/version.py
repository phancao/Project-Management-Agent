# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
Version and build information tracking.

This module provides version information including:
- Git commit hash
- Build timestamp
- Code file hash (for detecting code changes)
"""

import hashlib
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def get_git_commit_hash() -> str:
    """Get the current git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def get_git_commit_full_hash() -> str:
    """Get the full git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def get_git_commit_date() -> str:
    """Get the git commit date."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ci"],
            capture_output=True,
            text=True,
            check=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def get_code_hash(file_path: str) -> str:
    """Calculate SHA256 hash of a code file to detect changes."""
    try:
        with open(file_path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
            return file_hash[:16]  # Return first 16 chars for brevity
    except Exception:
        return "unknown"


def get_app_version_info() -> dict:
    """Get comprehensive version information."""
    # Get git info
    commit_hash = get_git_commit_hash()
    commit_full_hash = get_git_commit_full_hash()
    commit_date = get_git_commit_date()

    # Get code hash for key files
    base_path = Path(__file__).parent.parent.parent
    app_file = base_path / "src" / "server" / "app.py"
    code_hash = get_code_hash(str(app_file)) if app_file.exists() else "unknown"

    # Build timestamp (when this module was loaded)
    build_timestamp = datetime.utcnow().isoformat() + "Z"

    return {
        "version": "0.1.0",  # From pyproject.toml
        "commit_hash": commit_hash,
        "commit_full_hash": commit_full_hash,
        "commit_date": commit_date,
        "code_hash": code_hash,
        "build_timestamp": build_timestamp,
        "app_file": str(app_file.relative_to(base_path)) if app_file.exists() else "unknown",
    }


# Cache version info at module load time
_VERSION_INFO = get_app_version_info()


def get_version_info() -> dict:
    """Get cached version information."""
    return _VERSION_INFO.copy()


def log_version_info():
    """Log version information at startup."""
    info = get_version_info()
    logger.info("=" * 80)
    logger.info("🚀 Galaxy AI Project Manager API Server Starting")
    logger.info("=" * 80)
    logger.info(f"Version: {info['version']}")
    logger.info(f"Git Commit: {info['commit_hash']} ({info['commit_date']})")
    logger.info(f"Code Hash (app.py): {info['code_hash']}")
    logger.info(f"Build Timestamp: {info['build_timestamp']}")
    logger.info("=" * 80)

