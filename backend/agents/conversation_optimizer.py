import logging
from typing import List, Any
from langchain_core.messages import BaseMessage, SystemMessage
from backend.memory.conversation_memory import get_conversation_memory, ConversationMemory

logger = logging.getLogger(__name__)

class ConversationContextOptimizer:
    """
    Optimizes chat history for the agent's context.
    Uses ConversationMemory (RAG + Summarization) to provide a relevant subset 
    of history when the full history exceeds token limits.
    """
    
    def __init__(self):
        pass
        
    def get_optimized_history(
        self, 
        thread_id: str, 
        current_query: str, 
        raw_history: List[BaseMessage], 
        token_limit: int, 
        current_context_tokens: int
    ) -> List[BaseMessage]:
        """
        Returns optimized history if context is tight, otherwise returns raw history.
        
        Args:
            thread_id: Key for retrieving memory
            current_query: The user's latest question (for vector retrieval)
            raw_history: The linear list of messages from the graph state
            token_limit: The model's max token limit
            current_context_tokens: Current estimated token usage
            
        Returns:
            List[BaseMessage]: Useable history context
        """
        
        # 1. Check Safety Margin (e.g., 90% of limit)
        SAFE_THRESHOLD = 0.9
        
        if current_context_tokens < (token_limit * SAFE_THRESHOLD):
            # Safe to use full history
            return raw_history
            
        # 2. Context is full! Trigger RAG Optimization
        logger.info(f"[ConversationOptimizer] ⚠️ Context Usage {current_context_tokens}/{token_limit} tokens. Triggering RAG Optimization.")
        
        # 3. Get Memory Instance
        memory = get_conversation_memory(thread_id, create_if_missing=True)
        
        # 4. Sync Memory (Ensure current linear history is captured if not already)
        # Note: In a real graph, we might trust the graph state, but ConversationMemory 
        # needs to have indexed the messages to retrieve them.
        # Ideally, messages are added to memory as they happen. 
        # For now, we assume the system logic handles adding to memory, 
        # or we rely on what's already in the DB.
        
        # 5. Retrieve Optimized Context
        # This returns: [Summary] + [Retrieved Chunks] + [Recent Messages]
        optimized_messages = memory.get_context_messages(
            current_query=current_query,
            include_summary=True,
            include_retrieval=True,
            max_messages=10 # Keep last 10 messages raw
        )
        
        logger.info(f"[ConversationOptimizer] ✅ Optimized History: {len(raw_history)} -> {len(optimized_messages)} messages.")
        
        return optimized_messages
