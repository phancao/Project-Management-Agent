# Adaptive Agent Context Configuration
# Uses PERCENTAGE of model's context window for adaptability across models
# This allows the system to work with GPT-3.5 (16K), GPT-4o (128K), Claude (200K), etc.

from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

# Agent strategies use percentage of model context (0.0 to 1.0)
# This adapts to any model automatically
AGENT_CONTEXT_PERCENTAGES = {
    "planner": {
        "token_percent": 0.75,  # 75% of model context - needs big picture
        "preserve_prefix": 5,
        "compression_mode": "hierarchical",
        "description": "Planner needs full context"
    },
    "reporter": {
        "token_percent": 0.85,  # 85% of model context - needs all data
        "preserve_prefix": 2,
        "compression_mode": "importance_based",
        "description": "Reporter needs comprehensive data"
    },
    "pm_agent": {
        "token_percent": 0.60,  # 60% of model context
        "preserve_prefix": 3,
        "compression_mode": "hierarchical",
        "description": "PM agent needs recent context"
    },
    "researcher": {
        "token_percent": 0.60,  # 60% of model context
        "preserve_prefix": 3,
        "compression_mode": "hierarchical",
        "description": "Researcher needs search results"
    },
    "coder": {
        "token_percent": 0.50,  # 50% of model context
        "preserve_prefix": 2,
        "compression_mode": "importance_based",
        "description": "Coder focuses on code"
    },
    "react_agent": {
        "token_percent": 0.35,  # 35% of model context - fast & minimal
        "preserve_prefix": 1,
        "compression_mode": "simple",
        "description": "ReAct uses minimal context"
    },
    "coordinator": {
        "token_percent": 0.50,  # 50% of model context
        "preserve_prefix": 2,
        "compression_mode": "simple",
        "description": "Coordinator routes efficiently"
    },
    "validator": {
        "token_percent": 0.50,  # 50% of model context
        "preserve_prefix": 2,
        "compression_mode": "importance_based",
        "description": "Validator checks results"
    },
    "reflector": {
        "token_percent": 0.60,  # 60% of model context
        "preserve_prefix": 3,
        "compression_mode": "importance_based",
        "description": "Reflector analyzes failures"
    },
    "default": {
        "token_percent": 0.50,  # 50% - safe default
        "preserve_prefix": 3,
        "compression_mode": "hierarchical",
        "description": "Default strategy"
    }
}


def calculate_agent_token_limit(agent_type: str, model_context_limit: int) -> int:
    """
    Calculate adaptive token limit based on model's context window.
    
    Args:
        agent_type: Type of agent (e.g., 'reporter', 'react_agent')
        model_context_limit: Model's total context (e.g., 16385, 128000, 200000)
        
    Returns:
        Calculated token limit for the agent
        
    Examples:
        GPT-3.5 (16K):
            reporter: 16385 * 0.85 = 13,927 tokens
            react_agent: 16385 * 0.35 = 5,735 tokens
            
        GPT-4o (128K):
            reporter: 128000 * 0.85 = 108,800 tokens  
            react_agent: 128000 * 0.35 = 44,800 tokens
            
        Claude 3.5 (200K):
            reporter: 200000 * 0.85 = 170,000 tokens
            react_agent: 200000 * 0.35 = 70,000 tokens
    """
    strategy = AGENT_CONTEXT_PERCENTAGES.get(
        agent_type, 
        AGENT_CONTEXT_PERCENTAGES["default"]
    )
    
    token_percent = strategy.get("token_percent", 0.50)
    calculated_limit = int(model_context_limit * token_percent)
    
    # Ensure reasonable bounds
    final_limit = max(1000, min(calculated_limit, model_context_limit))
    
    logger.debug(
        f"[ADAPTIVE-CONTEXT] {agent_type}: "
        f"model_limit={model_context_limit}, percent={token_percent}, "
        f"calculated={final_limit}"
    )
    
    return final_limit


def get_agent_strategy(agent_type: str) -> dict:
    """Get strategy configuration for an agent."""
    return AGENT_CONTEXT_PERCENTAGES.get(
        agent_type,
        AGENT_CONTEXT_PERCENTAGES["default"]
    )


def get_adaptive_context_manager(
    agent_type: str,
    model_name: str,
    model_context_limit: int,
    frontend_history_messages: Optional[List] = None
):
    """
    Create ContextManager with adaptive token limits based on model.
    
    Args:
        agent_type: Type of agent
        model_name: Model name for tokenization
        model_context_limit: Model's total context window
        frontend_history_messages: Frontend conversation history
        
    Returns:
        ContextManager with model-adaptive limits
    """
    from backend.utils.context_manager import ContextManager
    from backend.utils.token_budget import get_token_budget_for_model
    
    logger.info(
        f"[ADAPTIVE-CONTEXT] 🔍 DEBUG: get_adaptive_context_manager called - "
        f"agent_type={agent_type}, model_name={model_name}, "
        f"model_context_limit={model_context_limit:,}, "
        f"frontend_messages={len(frontend_history_messages) if frontend_history_messages else 0}"
    )
    
    # Calculate agent-specific limit as percentage of model context
    agent_limit = calculate_agent_token_limit(agent_type, model_context_limit)
    logger.info(f"[ADAPTIVE-CONTEXT] 🔍 DEBUG: Calculated agent_limit: {agent_limit:,} tokens")
    
    strategy = get_agent_strategy(agent_type)
    logger.info(
        f"[ADAPTIVE-CONTEXT] 🔍 DEBUG: Strategy - "
        f"token_percent={strategy.get('token_percent', 0)}, "
        f"preserve_prefix={strategy.get('preserve_prefix', 0)}, "
        f"compression_mode={strategy.get('compression_mode', 'unknown')}"
    )
    
    # Create initial context manager
    initial_cm = ContextManager(
        token_limit=agent_limit,
        preserve_prefix_message_count=strategy["preserve_prefix"],
        compression_mode=strategy["compression_mode"],
        agent_type=agent_type,
        summary_model=model_name
    )
    logger.info(f"[ADAPTIVE-CONTEXT] 🔍 DEBUG: Initial context manager created - token_limit={initial_cm.token_limit}")
    
    # Adjust for frontend history if provided
    if frontend_history_messages:
        logger.info(f"[ADAPTIVE-CONTEXT] 🔍 DEBUG: Adjusting for frontend history ({len(frontend_history_messages)} messages)")
        budget = get_token_budget_for_model(model_name)
        adjusted_limit = budget.get_adjusted_limit_for_agent(
            agent_type,
            frontend_history_messages,
            initial_cm
        )
        logger.info(f"[ADAPTIVE-CONTEXT] 🔍 DEBUG: Adjusted limit: {adjusted_limit:,} tokens (was {agent_limit:,})")
        
        # Return new context manager with adjusted limit
        adjusted_cm = ContextManager(
            token_limit=adjusted_limit,
            preserve_prefix_message_count=strategy["preserve_prefix"],
            compression_mode=strategy["compression_mode"],
            agent_type=agent_type,
            summary_model=model_name
        )
        logger.info(f"[ADAPTIVE-CONTEXT] 🔍 DEBUG: Returning adjusted context manager - token_limit={adjusted_cm.token_limit}")
        return adjusted_cm
    
    logger.info(f"[ADAPTIVE-CONTEXT] 🔍 DEBUG: Returning initial context manager - token_limit={initial_cm.token_limit}")
    return initial_cm

