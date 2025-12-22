"""
Shared Prompts Package

This package provides shared prompt templates and utilities
for building agent prompts across PM Agent and Meeting Notes Agent.
"""

from shared.prompts.utils import (
    load_prompt,
    apply_template,
    get_prompt_path,
)

__all__ = [
    'load_prompt',
    'apply_template',
    'get_prompt_path',
]
