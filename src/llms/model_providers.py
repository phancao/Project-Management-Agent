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
PROVIDERS: Dict[str, ModelProvider] = {
    "openai": ModelProvider(
        id="openai",
        name="OpenAI",
        description="GPT-5.1, GPT-4o, GPT-4 Turbo, and more",
        base_url="https://api.openai.com/v1",
        models=[
            "gpt-5.1",
            "gpt-5.1-preview",
            "gpt-5-mini",
            "gpt-5-nano",
            "gpt-4o-2024-11-20",
            "gpt-4o-2024-08-06",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4-turbo-preview",
            "gpt-4",
            "gpt-3.5-turbo",
        ],
        icon="🤖",
    ),
    "anthropic": ModelProvider(
        id="anthropic",
        name="Anthropic",
        description="Claude Opus 4.5, Claude 3.5 Opus, Claude 3.5 Sonnet, and more",
        base_url="https://api.anthropic.com/v1",
        models=[
            "claude-opus-4.5",
            "claude-opus-4.5-20241124",
            "claude-3-5-opus-20241022",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-sonnet-20240620",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ],
        icon="🧠",
    ),
    "google": ModelProvider(
        id="google",
        name="Google AI Studio",
        description="Gemini 3 Pro, Gemini 3.5, Gemini 2.0, and more",
        base_url="https://generativelanguage.googleapis.com/v1",
        models=[
            "gemini-3-pro",
            "gemini-3-pro-20241118",
            "gemini-3.5",
            "gemini-3.5-pro",
            "gemini-2.0-flash-exp",
            "gemini-2.0-flash-thinking-exp",
            "gemini-1.5-pro",
            "gemini-1.5-pro-latest",
            "gemini-1.5-flash",
            "gemini-1.5-flash-latest",
            "gemini-pro",
        ],
        icon="🔮",
    ),
    "azure": ModelProvider(
        id="azure",
        name="Azure OpenAI",
        description="OpenAI models via Azure",
        base_url="",  # Varies by deployment
        models=["gpt-4", "gpt-4-turbo", "gpt-35-turbo"],
        icon="☁️",
    ),
    "ollama": ModelProvider(
        id="ollama",
        name="Ollama",
        description="Local models: Llama, Mistral, Qwen, and more",
        base_url="http://localhost:11434/v1",
        models=["llama3.2", "mistral", "qwen2.5", "phi3"],
        icon="🦙",
        requires_api_key=False,
    ),
    "deepseek": ModelProvider(
        id="deepseek",
        name="DeepSeek",
        description="DeepSeek Chat and Reasoning models",
        base_url="https://api.deepseek.com/v1",
        models=["deepseek-chat", "deepseek-reasoner"],
        icon="🔍",
    ),
    "dashscope": ModelProvider(
        id="dashscope",
        name="Dashscope (Alibaba)",
        description="Qwen models via Alibaba Cloud",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        models=["qwen-plus", "qwen-turbo", "qwen-max"],
        icon="🌏",
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

