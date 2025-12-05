# Agent-specific context configuration
# Based on Cursor/Copilot strategies - different agents need different context strategies
# Uses PERCENTAGE of model's context window for adaptability across models

from typing import Optional, List

# Agent strategies use percentage of model context (0.0 to 1.0)
# This adapts to any model: GPT-3.5 (16K), GPT-4o (128K), Claude (200K), etc.
AGENT_CONTEXT_STRATEGIES = {
    "planner": {
        "token_percent": 0.75,  # 75% of model context - needs big picture
        "preserve_prefix": 5,   # Keep system prompt + user query
        "compression_mode": "hierarchical",
        "description": "Planner needs full context to create comprehensive plans"
    },
    "reporter": {
        "token_percent": 0.85,  # 85% of model context - needs all data for report
        "preserve_prefix": 2,   # System prompt + current query
        "compression_mode": "importance_based",
        "description": "Reporter focuses on important findings and results"
    },
    "pm_agent": {
        "token_percent": 0.60,  # 60% of model context - PM data + recent context
        "preserve_prefix": 3,
        "compression_mode": "hierarchical",
        "description": "PM agent needs recent context + tool results"
    },
    "researcher": {
        "token_percent": 0.60,  # 60% of model context - search results + context
        "preserve_prefix": 3,
        "compression_mode": "hierarchical",
        "description": "Researcher needs search results + context"
    },
    "coder": {
        "token_percent": 0.50,  # 50% of model context - focused on code
        "preserve_prefix": 2,
        "compression_mode": "importance_based",
        "description": "Coder focuses on recent code + errors"
    },
    "react_agent": {
        "token_percent": 0.35,  # 35% of model context - minimal for speed
        "preserve_prefix": 1,
        "compression_mode": "simple",
        "description": "React agent uses minimal context for speed"
    },
    "coordinator": {
        "token_percent": 0.50,  # 50% of model context - routing decisions
        "preserve_prefix": 2,
        "compression_mode": "simple",
        "description": "Coordinator makes routing decisions"
    },
    "validator": {
        "token_percent": 0.50,  # 50% of model context - validates results
        "preserve_prefix": 2,
        "compression_mode": "importance_based",
        "description": "Validator focuses on results and errors"
    },
    "reflector": {
        "token_percent": 0.60,  # 60% of model context - needs failure context
        "preserve_prefix": 3,
        "compression_mode": "importance_based",
        "description": "Reflector analyzes failures for replanning"
    },
    "default": {
        "token_limit": 10000,  # Safe default
        "preserve_prefix": 3,
        "compression_mode": "hierarchical",
        "description": "Default strategy for unknown agents"
    }
}


def get_context_strategy(agent_type: str) -> dict:
    """
    Get context management strategy for an agent type.
    
    Args:
        agent_type: Type of agent (e.g., 'planner', 'reporter', 'coder')
        
    Returns:
        Dictionary with token_limit, preserve_prefix, and compression_mode
    """
    return AGENT_CONTEXT_STRATEGIES.get(agent_type, AGENT_CONTEXT_STRATEGIES["default"])


def get_context_manager_for_agent(
    agent_type: str, 
    summary_model: str = "gpt-3.5-turbo",
    frontend_history_messages: Optional[List] = None
):
    """
    Create optimized ContextManager for specific agent type.
    
    IMPORTANT: Adjusts token limits to account for frontend conversation history!
    
    Args:
        agent_type: Type of agent
        summary_model: Model to use for summarization
        frontend_history_messages: Messages from frontend (to calculate budget)
        
    Returns:
        Configured ContextManager instance with adjusted token limit
    """
    from src.utils.context_manager import ContextManager
    from src.utils.token_budget import get_token_budget_for_model
    
    strategy = get_context_strategy(agent_type)
    
    # Get model's context limit for percentage calculation
    from src.llms.llm import get_llm_token_limit_by_type
    from src.utils.adaptive_context_config import calculate_agent_token_limit
    
    # Get model's total context window
    model_limit = get_llm_token_limit_by_type("basic") or 16385
    
    # Calculate agent's token limit as percentage of model's context
    agent_token_limit = calculate_agent_token_limit(agent_type, model_limit)
    
    # Create initial context manager for token counting
    initial_cm = ContextManager(
        token_limit=agent_token_limit,
        preserve_prefix_message_count=strategy["preserve_prefix"],
        compression_mode=strategy["compression_mode"],
        agent_type=agent_type,
        summary_model=summary_model
    )
    
    # Adjust token limit if frontend history is provided
    if frontend_history_messages:
        budget = get_token_budget_for_model(summary_model)
        adjusted_limit = budget.get_adjusted_limit_for_agent(
            agent_type,
            frontend_history_messages,
            initial_cm
        )
        
        # Return new context manager with adjusted limit
        return ContextManager(
            token_limit=adjusted_limit,
            preserve_prefix_message_count=strategy["preserve_prefix"],
            compression_mode=strategy["compression_mode"],
            agent_type=agent_type,
            summary_model=summary_model
        )
    
    # No frontend history - use default
    return initial_cm

