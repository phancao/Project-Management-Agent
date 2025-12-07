# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""Model provider definitions and utilities."""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass

@dataclass
class ModelProvider:
    """Represents a model provider configuration."""
    id: str
    name: str
    description: str
    base_url: str
    models: List[str]
    icon: str = "🤖"  # Emoji or icon identifier
    requires_api_key: bool = True
    supports_streaming: bool = True

# Predefined model providers
# 
# THOUGHT EXTRACTION SUPPORT:
# - Reasoning models (o1 series): Provide reasoning_content automatically
# - All other models: Extract thoughts from content using "Thought:" pattern (like Cursor does)
# 
# This means ALL models can show thoughts - we prompt them to write "Thought:" before tool calls,
# then extract it from content. This works with any model, not just expensive reasoning models.
#
# REASONING MODELS (provide reasoning_content automatically):
# - OpenAI o1 series: o1-preview, o1 - Provide reasoning_content in API
#
# CONTENT-BASED MODELS (extract "Thought:" from content):
# - All GPT models (GPT-3.5, GPT-4, GPT-5, etc.)
# - OpenAI o3 series (o3-mini, o3) - May also support reasoning_content but we extract from content
# - DeepSeek models
# - Dashscope Qwen models
# - Google Gemini models
PROVIDERS: Dict[str, ModelProvider] = {
    "openai": ModelProvider(
        id="openai",
        name="OpenAI",
        description="OpenAI models - Reasoning models provide reasoning_content, others extract thoughts from content",
        base_url="https://api.openai.com/v1",
        models=[
            # Reasoning models (provide reasoning_content automatically)
            "o1-preview",  # $15.00/$60.00 per million | 128K context | 32K output
            "o1",          # $15.00/$60.00 per million | 200K context | 100K output
            
            # Content-based models (extract "Thought:" from content - like Cursor)
            "o3-mini",     # $1.10/$4.40 per million | 200K context | 100K output | CHEAPEST
            "o3",          # $2.00/$8.00 per million | 200K context | 100K output
            "gpt-5.1",     # GPT-5.1 flagship model | 400K context | 128K output
            "gpt-5.1-preview", # GPT-5.1 preview | 400K context | 128K output
            "gpt-5-mini",  # GPT-5 Mini - faster, cost-efficient | 400K context | 128K output
            "gpt-5-nano",  # GPT-5 Nano - lightweight, speed optimized | 400K context | 128K output
            "gpt-4o",      # Fast and capable
            "gpt-4o-mini", # Cheaper GPT-4 option
            "gpt-4-turbo", # GPT-4 Turbo
            "gpt-4",       # Standard GPT-4
            "gpt-3.5-turbo", # Cheapest option
        ],
        icon="🤖",
    ),
    "deepseek": ModelProvider(
        id="deepseek",
        name="DeepSeek",
        description="DeepSeek models - Extract thoughts from content (like Cursor)",
        base_url="https://api.deepseek.com/v1",
        models=[
            "deepseek-reasoner",  # Reasoning model
            "deepseek-chat",      # Standard chat model
        ],
        icon="🔍",
    ),
    "dashscope": ModelProvider(
        id="dashscope",
        name="Dashscope (Alibaba)",
        description="Qwen models - Extract thoughts from content (like Cursor)",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        models=[
            "qwen3-235b-a22b-thinking-2507",  # Thinking model
            "qwen-plus",                      # Standard Qwen model
            "qwen-turbo",                     # Fast Qwen model
        ],
        icon="🌏",
    ),
    "google": ModelProvider(
        id="google",
        name="Google AI Studio",
        description="Google Gemini models - Extract thoughts from content (like Cursor)",
        base_url="https://generativelanguage.googleapis.com/v1",
        models=[
            "gemini-2.0-flash-thinking-exp",  # Thinking model
            "gemini-2.0-flash-exp",            # Fast model
            "gemini-1.5-pro",                  # Pro model
            "gemini-1.5-flash",                # Flash model
        ],
        icon="🔮",
    ),
}

def get_available_providers() -> List[Dict[str, Any]]:
    """Get list of available model providers."""
    return [
        {
            "id": provider.id,
            "name": provider.name,
            "description": provider.description,
            "icon": provider.icon,
            "models": provider.models,
            "requires_api_key": provider.requires_api_key,
            "supports_streaming": provider.supports_streaming,
        }
        for provider in PROVIDERS.values()
    ]

def get_provider_by_id(provider_id: str) -> Optional[ModelProvider]:
    """Get a provider by its ID."""
    return PROVIDERS.get(provider_id)

def detect_provider_from_config(config: Dict[str, Any]) -> Optional[str]:
    """Detect provider type from configuration."""
    base_url = config.get("base_url", "").lower()
    platform = config.get("platform", "").lower()
    
    if "anthropic" in base_url or "anthropic" in platform:
        return "anthropic"
    elif "google" in base_url or "google" in platform or "generativelanguage" in base_url:
        return "google"
    elif "azure" in base_url or "azure" in platform:
        return "azure"
    elif "localhost:11434" in base_url or "ollama" in base_url:
        return "ollama"
    elif "deepseek" in base_url:
        return "deepseek"
    elif "dashscope" in base_url:
        return "dashscope"
    elif "openai" in base_url or not base_url:
        return "openai"
    
    return None

