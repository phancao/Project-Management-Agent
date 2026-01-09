import logging
import json
from typing import List, Dict, Any, Optional
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage
from backend.llms.llm import get_llm_token_limit_by_type
from backend.agents.pm_context_optimizer import PMToolContextOptimizer
from backend.agents.conversation_optimizer import ConversationContextOptimizer
from backend.utils.context_manager import ContextManager

logger = logging.getLogger(__name__)

class GlobalContextOptimizer:
    """
    The 'Bigger Context Optimizer' or 'System Context Optimizer'.
    Orchestrates the context assembly for all Agents.
    
    Responsibilities:
    1. Monitor Token Usage.
    2. Delegate Structured Data Optimization to PMContextOptimizer.
    3. Delegate History Optimization to ConversationContextOptimizer (RAG).
    """
    
    def __init__(self, model_type: str = "basic"):
        self.model_type = model_type
        self.pm_optimizer = PMToolContextOptimizer()
        self.conv_optimizer = ConversationContextOptimizer()
        
        # Initialize ContextManager for accurate token counting
        # We don't use its compression logic, just counting
        limit = get_llm_token_limit_by_type(model_type) or 128000
        self.context_manager = ContextManager(token_limit=limit)
        
    def _estimate_tokens(self, messages: List[BaseMessage]) -> int:
        """
        Accurate token counting using ContextManager (uses tiktoken if available).
        """
        return self.context_manager.count_tokens(messages)

    def assemble_context(
        self,
        thread_id: str,
        user_query: str,
        system_prompt: str,
        history: List[BaseMessage],
        tool_results: List[Dict[str, Any]] = None
    ) -> List[BaseMessage]:
        """
        Assembles and optimizes the final context for the LLM.
        
        Args:
            thread_id: Conversation ID
            user_query: Current user question
            system_prompt: The System Prompt string
            history: List of previous messages
            tool_results: Optional pending tool results to append
            
        Returns:
            List[BaseMessage]: The optimized message list ready for invocation.
        """
        
        # 1. Get Limits
        token_limit = get_llm_token_limit_by_type(self.model_type) or 128000 # Default to 128k if unknown
        
        # 2. Build Candidate Context (Standard Linear)
        messages: List[BaseMessage] = [SystemMessage(content=system_prompt)]
        messages.extend(history)
        
        # Append tool results if any (though usually they are part of history or steps)
        # Assuming tool_results here refers to *just executed* tools that need optimization
        # before being added to history.
        
        # 3. Calculate Usage
        current_tokens = self._estimate_tokens(messages)
        
        # 4. Trigger Global Optimization (Conversation History) if needed
        # Check against 90% threshold
        if current_tokens > (token_limit * 0.9):
            logger.warning(f"[GlobalOptimizer] 🚨 Context Full ({current_tokens}/{token_limit}). Optimizing Conversation History.")
            
            # Use RAG-optimized history instead of full linear history
            optimized_history = self.conv_optimizer.get_optimized_history(
                thread_id=thread_id,
                current_query=user_query,
                raw_history=history,
                token_limit=token_limit,
                current_context_tokens=current_tokens
            )
            
            # Rebuild Context
            messages = [SystemMessage(content=system_prompt)]
            messages.extend(optimized_history)
            
            new_tokens = self._estimate_tokens(messages)
            logger.info(f"[GlobalOptimizer] 📉 History Optimized: {current_tokens} -> {new_tokens} tokens")
            
        return messages

    async def optimize_tool_result(self, tool_name: str, result: str, user_query: str) -> str:
        """
        Delegates tool result optimization to the PM Optimizer.
        """
        return await self.pm_optimizer.optimize(user_query, tool_name, result)
