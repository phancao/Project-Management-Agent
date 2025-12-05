# Token Budget Coordinator
# Ensures frontend history + backend compression stay within model's total limit

import logging
from typing import List, Optional
from langchain_core.messages import BaseMessage

logger = logging.getLogger(__name__)


class TokenBudget:
    """
    Coordinates token usage between frontend history and backend compression.
    
    Problem:
    - Frontend sends last 20 messages (consumes ~4K tokens)
    - Backend adds system prompts (~1K tokens)
    - Agent generates tool results (~variable)
    - All must fit in model's limit (e.g., 16K for GPT-3.5)
    
    Solution:
    - Calculate tokens used by frontend history
    - Reserve budget for system prompts + agent overhead
    - Remaining budget → available for compression
    """
    
    # Token overhead estimates (conservative)
    SYSTEM_PROMPT_TOKENS = 1000      # System prompts per agent
    AGENT_REASONING_TOKENS = 2000     # Space for agent to think
    SAFETY_BUFFER_TOKENS = 500        # Safety margin
    
    def __init__(self, model_token_limit: int):
        """
        Initialize token budget coordinator.
        
        Args:
            model_token_limit: Total token limit for the model (e.g., 16385 for GPT-3.5)
        """
        self.total_limit = model_token_limit
        self.reserved = (
            self.SYSTEM_PROMPT_TOKENS + 
            self.AGENT_REASONING_TOKENS + 
            self.SAFETY_BUFFER_TOKENS
        )
        logger.info(f"[TOKEN-BUDGET] Total: {self.total_limit}, Reserved: {self.reserved}")
    
    def calculate_available_for_compression(
        self,
        frontend_history_tokens: int
    ) -> int:
        """
        Calculate how many tokens are available for compression.
        
        Formula:
        available = total_limit - reserved - frontend_history
        
        Args:
            frontend_history_tokens: Tokens used by frontend conversation history
            
        Returns:
            Available tokens for compression
        """
        available = self.total_limit - self.reserved - frontend_history_tokens
        
        logger.info(
            f"[TOKEN-BUDGET] Calculation: "
            f"{self.total_limit} (total) - {self.reserved} (reserved) - "
            f"{frontend_history_tokens} (history) = {available} (available)"
        )
        
        return max(1000, available)  # Minimum 1K tokens
    
    def get_adjusted_limit_for_agent(
        self,
        agent_type: str,
        frontend_messages: List[BaseMessage],
        context_manager
    ) -> int:
        """
        Get adjusted token limit for agent after accounting for frontend history.
        
        Args:
            agent_type: Type of agent (e.g., 'reporter', 'planner')
            frontend_messages: Messages from frontend conversation history
            context_manager: ContextManager instance (for token counting)
            
        Returns:
            Adjusted token limit for compression
        """
        # Count tokens in frontend history
        if frontend_messages:
            # Use the same model that will be used for the agent
            frontend_tokens = context_manager.count_tokens(
                frontend_messages, 
                model=context_manager.summary_model
            )
        else:
            frontend_tokens = 0
        
        # Calculate available budget
        available = self.calculate_available_for_compression(frontend_tokens)
        
        # Get agent's default limit (percentage-based)
        from src.utils.adaptive_context_config import calculate_agent_token_limit, get_agent_strategy
        
        # Get model's total context limit
        model_limit = self.total_limit
        
        # Calculate agent's limit as percentage of model context
        agent_default_limit = calculate_agent_token_limit(agent_type, model_limit)
        
        # Use the SMALLER of: agent's default OR available budget
        # This ensures we never exceed the model's total limit
        adjusted_limit = min(agent_default_limit, available)
        
        logger.info(
            f"[TOKEN-BUDGET] Agent '{agent_type}': "
            f"Default={agent_default_limit}, Available={available}, "
            f"Adjusted={adjusted_limit}"
        )
        
        return adjusted_limit


def get_token_budget_for_model(model_name: Optional[str] = None) -> TokenBudget:
    """
    Get token budget coordinator for a specific model.
    
    Args:
        model_name: Model name (e.g., 'gpt-3.5-turbo', 'gpt-4', 'claude-3-sonnet')
        
    Returns:
        TokenBudget instance with appropriate limits
    """
    # Model token limits (context windows)
    # Order matters: more specific patterns should come first
    MODEL_LIMITS = {
        # GPT-5 series (400K context) - most specific first
        "gpt-5.1-preview": 400000,
        "gpt-5.1": 400000,
        "gpt-5-mini": 400000,
        "gpt-5-nano": 400000,
        # GPT-4o series (128K context) - specific versions first
        "gpt-4o-mini": 128000,
        "gpt-4o-2024": 128000,
        "gpt-4o-2025": 128000,
        "gpt-4o": 128000,
        # GPT-4 Turbo series (128K context)
        "gpt-4-turbo-preview": 128000,
        "gpt-4-turbo": 128000,
        # GPT-3.5 series (16K context)
        "gpt-3.5-turbo-16k": 16385,
        "gpt-3.5-turbo": 16385,
        # GPT-4 base (8K context) - check after turbo variants
        "gpt-4": 8192,
        # Claude models (200K context)
        "claude-3-5-sonnet": 200000,
        "claude-3-opus": 200000,
        "claude-3-sonnet": 200000,
        "claude-3-haiku": 200000,
        # DeepSeek models (64K context)
        "deepseek-reasoner": 64000,
        "deepseek-chat": 64000,
    }
    
    # Default to GPT-3.5 limit if unknown
    if not model_name:
        limit = 16385
    else:
        # Find matching model (case-insensitive partial match)
        # More specific patterns are checked first due to dictionary order
        model_lower = model_name.lower()
        limit = next(
            (v for k, v in MODEL_LIMITS.items() if k in model_lower),
            16385  # Default
        )
    
    logger.info(f"[TOKEN-BUDGET] Model '{model_name}': limit={limit}")
    
    return TokenBudget(limit)

