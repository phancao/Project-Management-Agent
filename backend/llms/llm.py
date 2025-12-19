# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import os
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Dict, get_args, Optional

import httpx
from langchain_core.language_models import BaseChatModel
from langchain_deepseek import ChatDeepSeek
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from shared.config import load_yaml_config
from shared.config.agents import LLMType
from backend.llms.providers.dashscope import ChatDashscope
from backend.llms.providers.openai_reasoning import ChatOpenAIReasoning

logger = logging.getLogger(__name__)

# Cache for LLM instances
_llm_cache: dict[LLMType, BaseChatModel] = {}

# Context variables for model selection (set per request)
_model_provider_ctx: ContextVar[Optional[str]] = ContextVar("model_provider", default=None)
_model_name_ctx: ContextVar[Optional[str]] = ContextVar("model_name", default=None)


def set_model_selection(provider_id: Optional[str] = None, model_name: Optional[str] = None):
    """Set the model provider and model name for the current async context."""
    _model_provider_ctx.set(provider_id)
    _model_name_ctx.set(model_name)


def _get_config_file_path() -> str:
    """Get the path to the configuration file."""
    return str((Path(__file__).parent.parent.parent / "conf.yaml").resolve())


def _get_llm_type_config_keys() -> dict[str, str]:
    """Get mapping of LLM types to their configuration keys."""
    return {
        "reasoning": "REASONING_MODEL",
        "basic": "BASIC_MODEL",
        "vision": "VISION_MODEL",
        "code": "CODE_MODEL",
    }


def _get_env_llm_conf(llm_type: str) -> Dict[str, Any]:
    """
    Get LLM configuration from environment variables.
    Environment variables should follow the format: {LLM_TYPE}__{KEY}
    e.g., BASIC_MODEL__api_key, BASIC_MODEL__base_url
    """
    prefix = f"{llm_type.upper()}_MODEL__"
    conf = {}
    for key, value in os.environ.items():
        if key.startswith(prefix):
            conf_key = key[len(prefix) :].lower()
            conf[conf_key] = value
    return conf


def _get_db_llm_conf(llm_type: str) -> Dict[str, Any]:
    """
    Get LLM configuration from AI Provider database table.
    Returns empty dict if no provider is configured or if database is not available.
    """
    try:
        from database.connection import get_db_session
        from database.orm_models import AIProviderAPIKey
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            # Check if model selection is provided via context (from request)
            context_provider_id = _model_provider_ctx.get()
            context_model_name = _model_name_ctx.get()
            
            # Use context provider_id if provided, otherwise detect from config
            provider_id: Optional[str]
            if context_provider_id:
                provider_id = context_provider_id
            else:
                # Try to get provider from conf.yaml or env to determine which provider_id to look for
                conf = load_yaml_config(_get_config_file_path())
                llm_type_config_keys = _get_llm_type_config_keys()
                config_key = llm_type_config_keys.get(llm_type, "")
                yaml_conf = conf.get(config_key, {}) if config_key else {}
                env_conf = _get_env_llm_conf(llm_type)
                merged_conf = {**env_conf, **yaml_conf}
                
                # Get provider_id from config (could be in model name, base_url, or explicit provider_id)
                provider_id = merged_conf.get("provider_id")
                if not provider_id:
                    # Try to detect from base_url or model
                    base_url = merged_conf.get("base_url", "").lower()
                    if "openai" in base_url or not base_url:
                        provider_id = "openai"
                    elif "anthropic" in base_url:
                        provider_id = "anthropic"
                    elif "google" in base_url or "generativelanguage" in base_url:
                        provider_id = "google_aistudio"
                    elif "deepseek" in base_url:
                        provider_id = "deepseek"
                    elif "dashscope" in base_url or "aliyuncs" in base_url:
                        provider_id = "dashscope"
                    elif "localhost:11434" in base_url or "ollama" in base_url:
                        provider_id = "ollama"
                    else:
                        # Default to openai if can't detect
                        provider_id = "openai"
            
            # Query database for AI provider API key
            if not provider_id:
                return {}
                
            ai_provider = db.query(AIProviderAPIKey).filter(
                AIProviderAPIKey.provider_id == provider_id,
                AIProviderAPIKey.is_active.is_(True)
            ).first()
            
            if ai_provider and ai_provider.api_key:
                db_conf: Dict[str, Any] = {
                    "api_key": str(ai_provider.api_key),
                }
                if ai_provider.base_url:
                    db_conf["base_url"] = str(ai_provider.base_url)
                # Use context model_name if provided, otherwise use provider's default
                if context_model_name:
                    db_conf["model"] = context_model_name
                elif ai_provider.model_name:
                    # Access the actual value from the SQLAlchemy model instance
                    model_name_value = getattr(ai_provider, 'model_name', None)
                    if model_name_value:
                        db_conf["model"] = str(model_name_value)
                if ai_provider.additional_config:
                    db_conf.update(ai_provider.additional_config)
                return db_conf
            
            return {}
        finally:
            db.close()
    except Exception:
        # If database is not available or query fails, return empty dict
        # This allows fallback to conf.yaml or environment variables
        return {}


def _create_llm_use_conf(llm_type: LLMType, conf: Dict[str, Any]) -> BaseChatModel:
    """Create LLM instance using configuration."""
    llm_type_config_keys = _get_llm_type_config_keys()
    config_key = llm_type_config_keys.get(llm_type)

    if not config_key:
        raise ValueError(f"Unknown LLM type: {llm_type}")

    llm_conf = conf.get(config_key, {})
    if not isinstance(llm_conf, dict):
        raise ValueError(f"Invalid LLM configuration for {llm_type}: {llm_conf}")

    # Get configuration from database (AI Provider API keys)
    db_conf = _get_db_llm_conf(llm_type)
    
    # Get configuration from environment variables
    env_conf = _get_env_llm_conf(llm_type)

    # Merge configurations with priority: database > conf.yaml > environment variables
    # Database API keys take highest priority, but other settings from conf.yaml/env can still be used
    merged_conf = {**env_conf, **llm_conf, **db_conf}

    # Log the model being used for debugging
    model_name = merged_conf.get("model", "default")
    provider_name = merged_conf.get("provider_id", "unknown")
    logger.info(
        f"[LLM-CONFIG] Creating {llm_type} LLM: provider={provider_name}, model={model_name}, "
        f"base_url={merged_conf.get('base_url', 'default')}"
    )

    # Remove unnecessary parameters when initializing the client
    if "token_limit" in merged_conf:
        merged_conf.pop("token_limit")

    if not merged_conf:
        raise ValueError(f"No configuration found for LLM type: {llm_type}")

    # Add max_retries to handle rate limit errors
    if "max_retries" not in merged_conf:
        merged_conf["max_retries"] = 3

    # Handle SSL verification settings
    verify_ssl = merged_conf.pop("verify_ssl", True)

    # Create custom HTTP client if SSL verification is disabled
    if not verify_ssl:
        http_client = httpx.Client(verify=False)
        http_async_client = httpx.AsyncClient(verify=False)
        merged_conf["http_client"] = http_client
        merged_conf["http_async_client"] = http_async_client

    # Check if it's Google AI Studio platform based on configuration
    platform = merged_conf.get("platform", "").lower()
    is_google_aistudio = platform == "google_aistudio" or platform == "google-aistudio"

    if is_google_aistudio:
        # Handle Google AI Studio specific configuration
        gemini_conf = merged_conf.copy()

        # Map common keys to Google AI Studio specific keys
        if "api_key" in gemini_conf:
            gemini_conf["google_api_key"] = gemini_conf.pop("api_key")

        # Remove base_url and platform since Google AI Studio doesn't use them
        gemini_conf.pop("base_url", None)
        gemini_conf.pop("platform", None)

        # Remove unsupported parameters for Google AI Studio
        gemini_conf.pop("http_client", None)
        gemini_conf.pop("http_async_client", None)

        return ChatGoogleGenerativeAI(**gemini_conf)

    if "azure_endpoint" in merged_conf or os.getenv("AZURE_OPENAI_ENDPOINT"):
        return AzureChatOpenAI(**merged_conf)

    # Check if base_url is dashscope endpoint
    if "base_url" in merged_conf and "dashscope." in merged_conf["base_url"]:
        if llm_type == "reasoning":
            merged_conf["extra_body"] = {"enable_thinking": True}
        else:
            merged_conf["extra_body"] = {"enable_thinking": False}
        return ChatDashscope(**merged_conf)

    # Check if base_url is deepseek endpoint (for reasoning models)
    if llm_type == "reasoning" and "base_url" in merged_conf and "deepseek" in merged_conf["base_url"].lower():
        merged_conf["api_base"] = merged_conf.pop("base_url", None)
        return ChatDeepSeek(**merged_conf)
    
    # For OpenAI reasoning models (o1/o3), use ChatOpenAIReasoning which extracts reasoning_content
    # Check if this is an OpenAI reasoning model
    model_name = merged_conf.get("model", "").lower()
    is_openai_reasoning = any(
        model in model_name for model in ["o1", "o3"]
    )
    
    if llm_type == "reasoning" and is_openai_reasoning:
        return ChatOpenAIReasoning(**merged_conf)
    
    # For other models, use ChatOpenAI
    return ChatOpenAI(**merged_conf)


def has_configured_ai_providers() -> bool:
    """
    Check if any AI providers are configured in the database.
    Returns True if at least one active AI provider with API key exists.
    """
    try:
        from database.connection import get_db_session
        from database.orm_models import AIProviderAPIKey
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            count = db.query(AIProviderAPIKey).filter(
                AIProviderAPIKey.is_active.is_(True),
                AIProviderAPIKey.api_key.isnot(None)
            ).count()
            return count > 0
        finally:
            db.close()
    except Exception:
        # If database check fails, assume providers might be configured via conf.yaml/env
        # Return True to allow fallback behavior
        return True


def has_configured_pm_providers() -> bool:
    """
    Check if any PM providers are configured in the database.
    Returns True if at least one active PM provider exists.
    """
    try:
        from database.connection import get_db_session
        from database.orm_models import PMProviderConnection
        
        db_gen = get_db_session()
        db = next(db_gen)
        
        try:
            count = db.query(PMProviderConnection).filter(
                PMProviderConnection.is_active.is_(True)
            ).count()
            return count > 0
        finally:
            db.close()
    except Exception:
        # If database check fails, assume providers might be configured
        # Return True to allow fallback behavior
        return True


def get_llm_by_type(llm_type: LLMType) -> BaseChatModel:
    """
    Get LLM instance by type. Returns cached instance if available.
    Note: Cache is checked, but model from database is read fresh each time
    to ensure we use the latest model_name from database.
    """
    # Always create a new LLM instance to ensure we get the latest model from database
    # The database model_name might have changed, so we need to re-read it
    conf = load_yaml_config(_get_config_file_path())
    llm = _create_llm_use_conf(llm_type, conf)
    
    # Update cache with new instance
    _llm_cache[llm_type] = llm
    return llm


def get_configured_llm_models() -> dict[str, list[str]]:
    """
    Get all configured LLM models grouped by type.

    Returns:
        Dictionary mapping LLM type to list of configured model names.
    """
    try:
        conf = load_yaml_config(_get_config_file_path())
        llm_type_config_keys = _get_llm_type_config_keys()

        configured_models: dict[str, list[str]] = {}

        for llm_type in get_args(LLMType):
            # Get configuration from YAML file
            config_key = llm_type_config_keys.get(llm_type, "")
            yaml_conf = conf.get(config_key, {}) if config_key else {}

            # Get configuration from environment variables
            env_conf = _get_env_llm_conf(llm_type)

            # Merge configurations, with conf.yaml taking precedence over environment variables
            merged_conf = {**env_conf, **yaml_conf}

            # Check if model is configured
            model_name = merged_conf.get("model")
            if model_name:
                configured_models.setdefault(llm_type, []).append(model_name)

        return configured_models

    except Exception as e:
        # Log error and return empty dict to avoid breaking the application
        print(f"Warning: Failed to load LLM configuration: {e}")
        return {}


def _get_model_token_limit_defaults(model_name: str) -> Optional[int]:
    """
    Get default token limits for common models.
    Checks specific model names first, then falls back to general patterns.
    
    Args:
        model_name: The model name (e.g., "gpt-4o", "gpt-3.5-turbo", "claude-3-opus")
    
    Returns:
        Token limit if known, None otherwise
    """
    model_lower = model_name.lower()
    
    # ===== OpenAI Models =====
    # GPT-5 and newer
    if "gpt-5" in model_lower:
        return 400000
    if "gpt-4.1" in model_lower:
        return 1048576  # 1M tokens
    
    # o1 and o3 series (reasoning models)
    if "o1-pro" in model_lower or "o1-preview" in model_lower:
        return 200000
    if "o1" in model_lower:
        return 200000
    if "o3" in model_lower:
        return 200000
    
    # GPT-4o series (128k context)
    if "gpt-4o-mini" in model_lower:
        return 128000
    if "gpt-4o-audio" in model_lower or "gpt-4o-search" in model_lower:
        return 128000
    if "gpt-4o-2024" in model_lower or "gpt-4o-2025" in model_lower:
        return 128000
    if "gpt-4o" in model_lower:
        return 128000
    
    # GPT-4 Turbo series (128k context)
    if "gpt-4-turbo" in model_lower or "gpt-4-turbo-preview" in model_lower:
        return 128000
    if "gpt-4-0125" in model_lower or "gpt-4-1106" in model_lower:
        return 128000
    if "gpt-4-2024" in model_lower:
        return 128000
    
    # GPT-4 base models (8k context)
    if "gpt-4-0613" in model_lower or "gpt-4-0314" in model_lower:
        return 8192
    if "gpt-4" in model_lower:
        return 8192  # Default for older GPT-4
    
    # GPT-3.5 Turbo series (16k context)
    if "gpt-3.5-turbo-16k" in model_lower:
        return 16385
    if "gpt-3.5-turbo-0125" in model_lower or "gpt-3.5-turbo-1106" in model_lower:
        return 16385
    if "gpt-3.5-turbo" in model_lower:
        return 16385
    
    # GPT-3.5 Instruct (4k context)
    if "gpt-3.5-turbo-instruct" in model_lower:
        return 4096
    if "gpt-3.5" in model_lower:
        return 4096  # Default for GPT-3.5
    
    # ===== Anthropic Claude Models =====
    # Claude 3.5 series (200k context, expandable to 1M)
    if "claude-3-5-sonnet" in model_lower or "claude-3-5-haiku" in model_lower:
        return 200000
    if "claude-3-5" in model_lower:
        return 200000
    
    # Claude 3 series (200k context)
    if "claude-3-opus" in model_lower:
        return 200000
    if "claude-3-sonnet" in model_lower:
        return 200000
    if "claude-3-haiku" in model_lower:
        return 200000
    if "claude-3" in model_lower:
        return 200000
    
    # Claude 2 series (100k context)
    if "claude-2.1" in model_lower:
        return 200000
    if "claude-2" in model_lower:
        return 100000
    
    # Claude base (fallback)
    if "claude" in model_lower:
        return 100000  # Conservative default
    
    # ===== Google Gemini Models =====
    # Gemini 2.0 series
    if "gemini-2.0" in model_lower:
        return 1000000  # 1M context
    
    # Gemini 1.5 series (1M context)
    if "gemini-1.5-pro" in model_lower or "gemini-1.5-flash" in model_lower:
        return 1000000
    if "gemini-1.5" in model_lower:
        return 1000000
    
    # Gemini Pro series (32k-128k context depending on version)
    if "gemini-pro-1.5" in model_lower:
        return 1000000
    if "gemini-pro" in model_lower:
        return 32768  # Original Gemini Pro
    if "gemini" in model_lower:
        return 32768  # Default for Gemini
    
    # ===== DeepSeek Models =====
    # DeepSeek V3 series (128k context)
    if "deepseek-v3" in model_lower or "deepseek-v3.1" in model_lower or "deepseek-v3.2" in model_lower:
        return 128000
    if "deepseek-r1" in model_lower:
        return 128000
    if "deepseek-v2" in model_lower:
        return 128000
    if "deepseek" in model_lower:
        return 64000  # Default for DeepSeek
    
    # ===== Meta Llama Models =====
    # Llama 4 (1M context)
    if "llama-4" in model_lower or "llama4" in model_lower:
        return 1000000
    
    # Llama 3.3, 3.2, 3.1 (128k context)
    if "llama-3.3" in model_lower or "llama-3.2" in model_lower or "llama-3.1" in model_lower:
        return 128000
    if "llama-3" in model_lower or "llama3" in model_lower:
        return 8192  # Original Llama 3
    
    # Code Llama (16k context)
    if "code-llama" in model_lower or "codellama" in model_lower:
        return 16384
    
    # Llama 2 (4k context)
    if "llama-2" in model_lower or "llama2" in model_lower:
        return 4096
    if "llama" in model_lower:
        return 4096  # Default for Llama
    
    # ===== Mistral AI Models =====
    # Mistral Large 2 (128k context)
    if "mistral-large-2" in model_lower:
        return 128000
    if "mistral-large" in model_lower:
        return 32000
    if "mistral-medium" in model_lower:
        return 32000
    if "mistral-small" in model_lower:
        return 32000
    if "mistral" in model_lower:
        return 32000  # Default for Mistral
    
    # ===== Qwen Models =====
    # Qwen 3 series (128k context)
    if "qwen-3" in model_lower or "qwen3" in model_lower:
        return 128000
    if "qwen-2.5-vl" in model_lower:
        return 32000
    if "qwen-2" in model_lower or "qwen2" in model_lower:
        return 128000
    if "qwen" in model_lower:
        return 32000  # Default for Qwen
    
    # ===== xAI Grok Models =====
    # Grok series (128k context)
    if "grok-2" in model_lower:
        return 128000
    if "grok-1.5" in model_lower:
        return 128000
    if "grok" in model_lower:
        return 128000
    
    # ===== Cohere Models =====
    if "command-r-plus" in model_lower:
        return 128000
    if "command-r" in model_lower:
        return 128000
    if "command" in model_lower:
        return 4096
    if "cohere" in model_lower:
        return 4096
    
    # ===== AI21 Labs Models =====
    if "jamba" in model_lower:
        return 256000
    if "jurassic" in model_lower:
        return 8192
    if "ai21" in model_lower:
        return 8192
    
    # ===== Perplexity Models =====
    if "sonar" in model_lower or "perplexity" in model_lower:
        return 128000
    
    # ===== Other Common Models =====
    # PaLM models
    if "palm-2" in model_lower or "palm2" in model_lower:
        return 8192
    if "palm" in model_lower:
        return 4096
    
    # T5 models
    if "t5" in model_lower:
        return 512  # T5 has very small context
    
    # BERT models
    if "bert" in model_lower:
        return 512  # BERT has very small context
    
    # Default fallback for unknown models
    return None


def get_llm_token_limit_by_type(llm_type: str) -> Optional[int]:
    """
    Get the maximum token limit for a given LLM type.
    Checks database, config file, and falls back to model-specific defaults.

    Args:
        llm_type (str): The type of LLM.

    Returns:
        int: The maximum token limit for the specified LLM type, or None if not found.
    """
    llm_type_config_keys = _get_llm_type_config_keys()
    config_key = llm_type_config_keys.get(llm_type)
    if not config_key:
        return None

    # 1. Check database configuration (highest priority)
    try:
        db_conf = _get_db_llm_conf(llm_type)
        if db_conf.get("token_limit"):
            return int(db_conf["token_limit"])
        # Also check model name for defaults
        model_name = db_conf.get("model")
        if model_name:
            default_limit = _get_model_token_limit_defaults(model_name)
            if default_limit:
                return default_limit
    except Exception:
        pass  # Fall through to other sources

    # 2. Check conf.yaml
    try:
        conf = load_yaml_config(_get_config_file_path())
        llm_max_token = conf.get(config_key, {}).get("token_limit")
        if llm_max_token:
            return int(llm_max_token)
        
        # Also check model name for defaults
        model_name = conf.get(config_key, {}).get("model")
        if model_name:
            default_limit = _get_model_token_limit_defaults(model_name)
            if default_limit:
                return default_limit
    except Exception:
        pass  # Fall through to environment variables

    # 3. Check environment variables
    try:
        env_conf = _get_env_llm_conf(llm_type)
        if env_conf.get("token_limit"):
            return int(env_conf["token_limit"])
        # Also check model name for defaults
        model_name = env_conf.get("model")
        if model_name:
            default_limit = _get_model_token_limit_defaults(model_name)
            if default_limit:
                return default_limit
    except Exception:
        pass

    # 4. No token limit found anywhere
    return None


# In the future, we will use reasoning_llm and vl_llm for different purposes
# reasoning_llm = get_llm_by_type("reasoning")
# vl_llm = get_llm_by_type("vision")
