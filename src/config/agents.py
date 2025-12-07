# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from typing import Literal

# Define available LLM types
LLMType = Literal["basic", "reasoning", "vision", "code"]

# Define agent-LLM mapping
# NOTE: All agents can use "basic" models now - we extract thoughts from content (like Cursor)
# Reasoning models provide reasoning_content automatically, but basic models work too
# We prompt models to write "Thought:" before tool calls, then extract it from content
AGENT_LLM_MAP: dict[str, LLMType] = {
    "coordinator": "basic",  # Can use basic models - thoughts extracted from content
    "planner": "basic",  # Can use basic models - thoughts extracted from content
    "researcher": "basic",  # Can use basic models - thoughts extracted from content
    "coder": "basic",  # Can use basic models - thoughts extracted from content
    "reporter": "basic",  # Can use basic models - thoughts extracted from content
    "pm_agent": "basic",  # Can use basic models - thoughts extracted from content
    "podcast_script_writer": "basic",
    "ppt_composer": "basic",
    "prose_writer": "basic",
    "prompt_enhancer": "basic",
}
