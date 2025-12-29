# Copyright (c) 2025
# SPDX-License-Identifier: MIT

"""
Conversation Memory System

Implements a hybrid memory system for managing conversation context:
1. Short-term memory: Last N messages (full text)
2. Working memory: Summarized history of older messages
3. Long-term memory: Vector store for semantic retrieval

This approach prevents context overflow while maintaining conversation continuity.
"""

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


@dataclass
class ConversationMessage:
    """Represents a single message in the conversation."""
    
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    message_id: str = ""
    
    def __post_init__(self):
        if not self.message_id:
            # Generate a unique ID based on content and timestamp
            hash_input = f"{self.role}:{self.content}:{self.timestamp.isoformat()}"
            self.message_id = hashlib.md5(hash_input.encode()).hexdigest()[:12]
    
    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "message_id": self.message_id,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ConversationMessage":
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
            message_id=data.get("message_id", ""),
        )
    
    def to_langchain_message(self) -> BaseMessage:
        """Convert to LangChain message format."""
        if self.role == "user":
            return HumanMessage(content=self.content)
        elif self.role == "assistant":
            return AIMessage(content=self.content)
        elif self.role == "system":
            return SystemMessage(content=self.content)
        else:
            return HumanMessage(content=self.content)


class ConversationMemory:
    """
    Hybrid conversation memory system.
    
    Manages three levels of memory:
    1. Short-term: Recent messages kept in full
    2. Working: Summarized older messages
    3. Long-term: Vector store for semantic retrieval
    """
    
    def __init__(
        self,
        thread_id: str,
        short_term_limit: int = 10,
        max_tokens: int = 8000,
        enable_vector_store: bool = True,
        enable_summarization: bool = True,
        vector_store_path: str | None = None,
    ):
        """
        Initialize conversation memory.
        
        Args:
            thread_id: Unique identifier for this conversation
            short_term_limit: Number of recent messages to keep in full
            max_tokens: Maximum tokens for context window
            enable_vector_store: Whether to use vector store for retrieval
            enable_summarization: Whether to summarize older messages
            vector_store_path: Path for vector store (default: ./data/memory)
        """
        self.thread_id = thread_id
        self.short_term_limit = short_term_limit
        self.max_tokens = max_tokens
        self.enable_vector_store = enable_vector_store
        self.enable_summarization = enable_summarization
        
        # Memory stores
        self.messages: list[ConversationMessage] = []
        self.summary: str = ""
        self.summary_message_count: int = 0  # How many messages are summarized
        
        # Vector store setup
        self.vector_store = None
        self.embeddings = None
        self.vector_store_path = vector_store_path or os.path.join(
            os.path.dirname(__file__), "..", "..", "data", "memory"
        )
        
        if enable_vector_store:
            self._init_vector_store()
    
    def _init_vector_store(self):
        """Initialize the vector store for semantic retrieval."""
        try:
            from langchain_openai import OpenAIEmbeddings
            from pymilvus import MilvusClient
            
            # Use OpenAI embeddings (or configure based on env)
            embedding_model = os.getenv("MEMORY_EMBEDDING_MODEL", "text-embedding-3-small")
            self.embeddings = OpenAIEmbeddings(model=embedding_model)
            
            # Create data directory if it doesn't exist
            os.makedirs(self.vector_store_path, exist_ok=True)
            
            # Use Milvus Lite (file-based)
            db_path = os.path.join(self.vector_store_path, f"memory_{self.thread_id}.db")
            self.vector_store = MilvusClient(db_path)
            
            # Create collection if it doesn't exist
            collection_name = f"conv_{self.thread_id[:8]}"
            if not self.vector_store.has_collection(collection_name):
                self.vector_store.create_collection(
                    collection_name=collection_name,
                    dimension=1536,  # OpenAI embedding dimension
                    metric_type="COSINE",
                )
            self.collection_name = collection_name
            
            logger.info(f"[ConversationMemory] Vector store initialized for thread {self.thread_id}")
            
        except Exception as e:
            logger.warning(f"[ConversationMemory] Failed to initialize vector store: {e}")
            self.enable_vector_store = False
            self.vector_store = None
    
    def add_message(self, role: str, content: str, metadata: dict[str, Any] | None = None) -> ConversationMessage:
        """
        Add a message to the conversation memory.
        
        Args:
            role: Message role ("user", "assistant", "system")
            content: Message content
            metadata: Optional metadata
            
        Returns:
            The created ConversationMessage
        """
        message = ConversationMessage(
            role=role,
            content=content,
            metadata=metadata or {},
        )
        
        self.messages.append(message)
        
        # Add to vector store for retrieval
        if self.enable_vector_store and self.vector_store and self.embeddings:
            try:
                self._add_to_vector_store(message)
            except Exception as e:
                logger.warning(f"[ConversationMemory] Failed to add to vector store: {e}")
        
        # Check if we need to summarize older messages
        if self.enable_summarization and len(self.messages) > self.short_term_limit * 2:
            self._maybe_summarize()
        
        return message
    
    def _add_to_vector_store(self, message: ConversationMessage):
        """Add a message to the vector store."""
        if not self.vector_store or not self.embeddings:
            return
            
        try:
            # Create embedding
            embedding = self.embeddings.embed_query(message.content)
            
            # Insert into Milvus
            self.vector_store.insert(
                collection_name=self.collection_name,
                data=[{
                    "id": hash(message.message_id) % (2**63),  # Milvus needs int64 ID
                    "vector": embedding,
                    "role": message.role,
                    "content": message.content,
                    "timestamp": message.timestamp.isoformat(),
                    "message_id": message.message_id,
                }]
            )
        except Exception as e:
            logger.warning(f"[ConversationMemory] Vector store insert failed: {e}")
    
    def _maybe_summarize(self):
        """Summarize older messages if needed."""
        # Only summarize if we have enough messages beyond the short-term limit
        messages_to_summarize = len(self.messages) - self.short_term_limit
        
        if messages_to_summarize <= self.summary_message_count:
            return  # Already summarized
        
        try:
            from langchain_openai import ChatOpenAI
            
            # Get messages to summarize (excluding recent ones)
            old_messages = self.messages[:messages_to_summarize]
            
            # Create summary prompt
            conversation_text = "\n".join([
                f"{msg.role}: {msg.content[:500]}..."  # Truncate long messages
                if len(msg.content) > 500 else f"{msg.role}: {msg.content}"
                for msg in old_messages
            ])
            
            summary_prompt = f"""Summarize the following conversation concisely, preserving key information, decisions, and context that would be important for continuing the conversation:

{conversation_text}

Summary:"""
            
            # Use a fast model for summarization
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
            response = llm.invoke(summary_prompt)
            
            self.summary = response.content
            self.summary_message_count = messages_to_summarize
            
            logger.info(f"[ConversationMemory] Summarized {messages_to_summarize} messages")
            
        except Exception as e:
            logger.warning(f"[ConversationMemory] Summarization failed: {e}")
    
    def retrieve_relevant_context(self, query: str, top_k: int = 5) -> list[ConversationMessage]:
        """
        Retrieve relevant past messages using semantic search.
        
        Args:
            query: The query to search for
            top_k: Number of results to return
            
        Returns:
            List of relevant ConversationMessages
        """
        if not self.enable_vector_store or not self.vector_store or not self.embeddings:
            return []
        
        try:
            # Create query embedding
            query_embedding = self.embeddings.embed_query(query)
            
            # Search in Milvus
            results = self.vector_store.search(
                collection_name=self.collection_name,
                data=[query_embedding],
                limit=top_k,
                output_fields=["role", "content", "timestamp", "message_id"],
            )
            
            # Convert results to ConversationMessages
            relevant_messages = []
            for hits in results:
                for hit in hits:
                    entity = hit.get("entity", {})
                    msg = ConversationMessage(
                        role=entity.get("role", "user"),
                        content=entity.get("content", ""),
                        timestamp=datetime.fromisoformat(entity.get("timestamp", datetime.now().isoformat())),
                        message_id=entity.get("message_id", ""),
                    )
                    relevant_messages.append(msg)
            
            return relevant_messages
            
        except Exception as e:
            logger.warning(f"[ConversationMemory] Retrieval failed: {e}")
            return []
    
    def get_context_messages(
        self,
        current_query: str | None = None,
        include_summary: bool = True,
        include_retrieval: bool = True,
        max_messages: int | None = None,
    ) -> list[BaseMessage]:
        """
        Get messages for LLM context.
        
        This builds an optimized context window with:
        1. Summary of older messages (if available)
        2. Retrieved relevant context (if query provided)
        3. Recent messages in full
        
        Args:
            current_query: Current user query for retrieval
            include_summary: Whether to include conversation summary
            include_retrieval: Whether to include retrieved context
            max_messages: Maximum number of recent messages
            
        Returns:
            List of LangChain BaseMessages ready for LLM
        """
        context_messages: list[BaseMessage] = []
        
        # 1. Add summary of older messages
        if include_summary and self.summary:
            summary_content = f"[Previous conversation summary]\n{self.summary}"
            context_messages.append(SystemMessage(content=summary_content))
        
        # 2. Add retrieved relevant context
        if include_retrieval and current_query and self.enable_vector_store:
            relevant = self.retrieve_relevant_context(current_query, top_k=3)
            if relevant:
                # Filter out messages that are already in recent history
                recent_ids = {msg.message_id for msg in self.messages[-self.short_term_limit:]}
                unique_relevant = [msg for msg in relevant if msg.message_id not in recent_ids]
                
                if unique_relevant:
                    relevant_text = "\n".join([
                        f"{msg.role}: {msg.content}" for msg in unique_relevant
                    ])
                    context_messages.append(SystemMessage(
                        content=f"[Relevant context from earlier in conversation]\n{relevant_text}"
                    ))
        
        # 3. Add recent messages
        limit = max_messages or self.short_term_limit
        recent_messages = self.messages[-limit:]
        
        for msg in recent_messages:
            context_messages.append(msg.to_langchain_message())
        
        
        return context_messages
    
    def get_full_history(self) -> list[dict]:
        """Get full conversation history as dictionaries."""
        return [msg.to_dict() for msg in self.messages]
    
    def clear(self):
        """Clear all memory."""
        self.messages = []
        self.summary = ""
        self.summary_message_count = 0
        
        # Clear vector store
        if self.vector_store:
            try:
                self.vector_store.drop_collection(self.collection_name)
                self._init_vector_store()  # Recreate collection
            except Exception as e:
                logger.warning(f"[ConversationMemory] Failed to clear vector store: {e}")
    
    def to_json(self) -> str:
        """Serialize memory to JSON."""
        return json.dumps({
            "thread_id": self.thread_id,
            "messages": [msg.to_dict() for msg in self.messages],
            "summary": self.summary,
            "summary_message_count": self.summary_message_count,
        })
    
    @classmethod
    def from_json(cls, json_str: str, **kwargs) -> "ConversationMemory":
        """Deserialize memory from JSON."""
        data = json.loads(json_str)
        memory = cls(thread_id=data["thread_id"], **kwargs)
        memory.messages = [ConversationMessage.from_dict(m) for m in data["messages"]]
        memory.summary = data.get("summary", "")
        memory.summary_message_count = data.get("summary_message_count", 0)
        return memory


class ConversationMemoryManager:
    """
    Manages multiple conversation memories.
    
    Provides a singleton-like interface for accessing conversation memories
    across different threads/sessions.
    """
    
    _instance: "ConversationMemoryManager | None" = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._memories: dict[str, ConversationMemory] = {}
        return cls._instance
    
    def get_memory(
        self,
        thread_id: str,
        create_if_missing: bool = True,
        **kwargs,
    ) -> ConversationMemory | None:
        """
        Get or create a conversation memory for a thread.
        
        Args:
            thread_id: Unique thread identifier
            create_if_missing: Whether to create if not exists
            **kwargs: Arguments passed to ConversationMemory constructor
            
        Returns:
            ConversationMemory instance or None
        """
        if thread_id not in self._memories:
            if create_if_missing:
                self._memories[thread_id] = ConversationMemory(thread_id, **kwargs)
                logger.info(f"[ConversationMemoryManager] Created memory for thread {thread_id}")
            else:
                return None
        
        return self._memories[thread_id]
    
    def delete_memory(self, thread_id: str) -> bool:
        """Delete a conversation memory."""
        if thread_id in self._memories:
            self._memories[thread_id].clear()
            del self._memories[thread_id]
            logger.info(f"[ConversationMemoryManager] Deleted memory for thread {thread_id}")
            return True
        return False
    
    def list_threads(self) -> list[str]:
        """List all active thread IDs."""
        return list(self._memories.keys())
    
    def get_stats(self) -> dict:
        """Get statistics about all memories."""
        return {
            "total_threads": len(self._memories),
            "threads": {
                tid: {
                    "message_count": len(mem.messages),
                    "has_summary": bool(mem.summary),
                    "summary_count": mem.summary_message_count,
                }
                for tid, mem in self._memories.items()
            }
        }


# Global instance
memory_manager = ConversationMemoryManager()


def get_conversation_memory(thread_id: str, **kwargs) -> ConversationMemory:
    """Convenience function to get conversation memory."""
    return memory_manager.get_memory(thread_id, **kwargs)

