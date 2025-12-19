# src/utils/token_manager.py
import copy
import json
import logging
from typing import List, Optional

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from shared.config import load_yaml_config

logger = logging.getLogger(__name__)

# Try to import tiktoken for accurate token counting
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logger.warning("tiktoken not available, falling back to character-based estimation")


def get_search_config():
    config = load_yaml_config("conf.yaml")
    search_config = config.get("MODEL_TOKEN_LIMITS", {})
    return search_config


class ContextManager:
    """Context manager and compression class"""

    def __init__(
        self, 
        token_limit: int, 
        preserve_prefix_message_count: int = 0,
        compression_mode: str = "hierarchical",
        agent_type: str = "default",
        summary_model: str = "gpt-3.5-turbo"
    ):
        """
        Initialize ContextManager

        Args:
            token_limit: Maximum token limit
            preserve_prefix_message_count: Number of messages to preserve at the beginning of the context
            compression_mode: Compression strategy ('simple', 'hierarchical', 'importance_based')
            agent_type: Type of agent using this context manager (affects strategy)
            summary_model: Model to use for summarization (default: gpt-3.5-turbo for speed)
        """
        self.token_limit = token_limit
        self.preserve_prefix_message_count = preserve_prefix_message_count
        self.compression_mode = compression_mode
        self.agent_type = agent_type
        self.summary_model = summary_model
        self.summary_cache = {}  # Cache summaries to avoid re-summarization

    def count_tokens(self, messages: List[BaseMessage], model: Optional[str] = None) -> int:
        """
        Count tokens in message list using accurate tokenizer if available

        Args:
            messages: List of messages
            model: Model name to determine tokenizer (e.g., 'gpt-3.5-turbo', 'gpt-4')

        Returns:
            Number of tokens
        """
        # Use tiktoken for accurate counting if available
        if TIKTOKEN_AVAILABLE and model:
            return self._count_tokens_with_tiktoken(messages, model)
        
        # Fallback to character-based estimation
        total_tokens = 0
        for message in messages:
            total_tokens += self._count_message_tokens(message)
        return total_tokens
    
    def _count_tokens_with_tiktoken(self, messages: List[BaseMessage], model: str) -> int:
        """
        Count tokens using tiktoken for accurate results.
        This matches OpenAI's actual token counting by formatting messages the same way LangChain does.
        
        Args:
            messages: List of messages
            model: Model name (e.g., 'gpt-3.5-turbo', 'gpt-4')
            
        Returns:
            Accurate token count
        """
        try:
            # Use LangChain's built-in token counting if available
            try:
                from langchain_openai import ChatOpenAI
                # Create a temporary LLM instance to use its token counting
                temp_llm = ChatOpenAI(model=model, temperature=0)
                # Use the LLM's get_num_tokens_from_messages if available
                if hasattr(temp_llm, 'get_num_tokens_from_messages'):
                    return temp_llm.get_num_tokens_from_messages(messages)
            except (ImportError, AttributeError, Exception) as e:
                logger.debug(f"LangChain token counting not available: {e}, using manual counting")
            
            # Manual counting: format messages like OpenAI API expects
            # Use tiktoken.encoding_for_model() for accurate model-specific encoding
            # This automatically selects the correct encoding (cl100k_base for GPT-3.5/4, etc.)
            try:
                # Try to get encoding for the specific model
                encoding = tiktoken.encoding_for_model(model)
            except (KeyError, ValueError):
                # Fallback: try to infer encoding from model name
                model_lower = model.lower()
                if "gpt-4" in model_lower or "gpt-3.5" in model_lower or "gpt-4o" in model_lower:
                    encoding = tiktoken.get_encoding("cl100k_base")
                elif "gpt-3" in model_lower:
                    encoding = tiktoken.get_encoding("p50k_base")
                else:
                    # Default to cl100k_base (most common for modern models)
                    encoding = tiktoken.get_encoding("cl100k_base")
                    logger.warning(f"Unknown model '{model}', using cl100k_base encoding")
            
            # Format messages like OpenAI API (same as LangChain does)
            # OpenAI format: [{"role": "system", "content": "..."}, ...]
            formatted_messages = []
            for message in messages:
                # CRITICAL: Handle both dict messages AND BaseMessage objects
                if isinstance(message, dict):
                    # Message is already a dict (from apply_prompt_template)
                    msg_dict = {
                        "role": message.get("role", "user"),
                        "content": str(message.get("content", ""))
                    }
                    if "name" in message:
                        msg_dict["name"] = message["name"]
                    if "tool_calls" in message:
                        msg_dict["tool_calls"] = message["tool_calls"]
                    if "tool_call_id" in message:
                        msg_dict["tool_call_id"] = message["tool_call_id"]
                    formatted_messages.append(msg_dict)
                    continue
                
                msg_dict = {}
                
                # Map LangChain message types to OpenAI roles
                if isinstance(message, SystemMessage):
                    msg_dict["role"] = "system"
                elif isinstance(message, HumanMessage):
                    msg_dict["role"] = "user"
                elif isinstance(message, AIMessage):
                    msg_dict["role"] = "assistant"
                elif isinstance(message, ToolMessage):
                    msg_dict["role"] = "tool"
                else:
                    # Default based on type attribute
                    role = getattr(message, "type", "user")
                    if role == "system":
                        msg_dict["role"] = "system"
                    elif role in ("user", "human"):
                        msg_dict["role"] = "user"
                    elif role in ("assistant", "ai"):
                        msg_dict["role"] = "assistant"
                    elif role == "tool":
                        msg_dict["role"] = "tool"
                    else:
                        msg_dict["role"] = "user"
                
                # Add content
                if hasattr(message, "content") and message.content:
                    msg_dict["content"] = str(message.content)
                else:
                    msg_dict["content"] = ""
                
                # Add name if present
                if hasattr(message, "name") and message.name:
                    msg_dict["name"] = message.name
                
                # Add tool_calls if present (AIMessage with tool calls)
                if isinstance(message, AIMessage) and hasattr(message, "tool_calls") and message.tool_calls:
                    msg_dict["tool_calls"] = message.tool_calls
                
                # Add tool_call_id if present (ToolMessage)
                if isinstance(message, ToolMessage) and hasattr(message, "tool_call_id"):
                    msg_dict["tool_call_id"] = message.tool_call_id
                
                formatted_messages.append(msg_dict)
            
            # Count tokens in the formatted messages (OpenAI's way)
            # Per OpenAI: tokens = 4 (base overhead) + sum of message tokens
            # Each message: role tokens + content tokens + name tokens (if present) + tool_calls tokens (if present)
            total_tokens = 4  # Base overhead per OpenAI
            
            for msg in formatted_messages:
                # Role tokens
                role_str = msg.get("role", "user")
                total_tokens += len(encoding.encode(role_str))
                
                # Content tokens
                content = msg.get("content", "")
                if content:
                    total_tokens += len(encoding.encode(str(content)))
                
                # Name tokens (if present)
                if "name" in msg and msg["name"]:
                    total_tokens += len(encoding.encode(str(msg["name"])))
                
                # Tool calls tokens (if present)
                if "tool_calls" in msg and msg["tool_calls"]:
                    for tool_call in msg["tool_calls"]:
                        # Format: {"id": "...", "type": "function", "function": {"name": "...", "arguments": "..."}}
                        tool_call_str = json.dumps(tool_call, ensure_ascii=False)
                        total_tokens += len(encoding.encode(tool_call_str))
                
                # Tool call ID (for tool messages)
                if "tool_call_id" in msg and msg["tool_call_id"]:
                    total_tokens += len(encoding.encode(str(msg["tool_call_id"])))
            
            return total_tokens
            
        except Exception as e:
            logger.warning(f"Failed to count tokens with tiktoken: {e}, falling back to estimation")
            # Fallback to character-based estimation
        total_tokens = 0
        for message in messages:
            total_tokens += self._count_message_tokens(message)
        return total_tokens

    def _count_message_tokens(self, message: BaseMessage) -> int:
        """
        Count tokens in a single message

        Args:
            message: Message object

        Returns:
            Number of tokens
        """
        # Estimate token count based on character length (different calculation for English and non-English)
        token_count = 0

        # Count tokens in content field
        if hasattr(message, "content") and message.content:
            # Handle different content types
            if isinstance(message.content, str):
                token_count += self._count_text_tokens(message.content)

        # Count role-related tokens
        if hasattr(message, "type"):
            token_count += self._count_text_tokens(message.type)

        # Special handling for different message types
        if isinstance(message, SystemMessage):
            # System messages are usually short but important, slightly increase estimate
            token_count = int(token_count * 1.1)
        elif isinstance(message, HumanMessage):
            # Human messages use normal estimation
            pass
        elif isinstance(message, AIMessage):
            # AI messages may contain reasoning content, slightly increase estimate
            token_count = int(token_count * 1.2)
        elif isinstance(message, ToolMessage):
            # Tool messages may contain large amounts of structured data, increase estimate
            token_count = int(token_count * 1.3)

        # Process additional information in additional_kwargs
        if hasattr(message, "additional_kwargs") and message.additional_kwargs:
            # Simple estimation of extra field tokens
            extra_str = str(message.additional_kwargs)
            token_count += self._count_text_tokens(extra_str)

            # If there are tool_calls, add estimation
            if "tool_calls" in message.additional_kwargs:
                token_count += 50  # Add estimation for function call information

        # Ensure at least 1 token
        return max(1, token_count)

    def _count_text_tokens(self, text: str) -> int:
        """
        Count tokens in text with different calculations for English and non-English characters.
        English characters: 4 characters ≈ 1 token
        Non-English characters (e.g., Chinese): 1 character ≈ 1 token

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        if not text:
            return 0

        english_chars = 0
        non_english_chars = 0

        for char in text:
            # Check if character is ASCII (English letters, digits, punctuation)
            if ord(char) < 128:
                english_chars += 1
            else:
                non_english_chars += 1

        # Calculate tokens: English at 4 chars/token, others at 1 char/token
        english_tokens = english_chars // 4
        non_english_tokens = non_english_chars

        return english_tokens + non_english_tokens

    def is_over_limit(self, messages: List[BaseMessage]) -> bool:
        """
        Check if messages exceed token limit

        Args:
            messages: List of messages

        Returns:
            Whether limit is exceeded
        """
        try:
            model = getattr(self, '_model_name', None)
            token_count = self.count_tokens(messages, model=model)
        except Exception as e:
            logger.warning(f"[CONTEXT-MANAGER] Failed to count tokens in is_over_limit with model, trying without: {e}")
            token_count = self.count_tokens(messages)
        
        is_over = token_count > self.token_limit
        logger.info(
            f"[CONTEXT-MANAGER] 🔍 DEBUG: is_over_limit - "
            f"Token count: {token_count:,}, "
            f"Token limit: {self.token_limit:,}, "
            f"Over limit: {is_over}"
        )
        return is_over

    def compress_messages(self, state: dict) -> dict:
        """
        Compress messages to fit within token limit

        Args:
            state: state with original messages

        Returns:
            Compressed state with compressed messages and optimization metadata
        """
        logger.info(f"[CONTEXT-MANAGER] 🔍 DEBUG: compress_messages called - token_limit={self.token_limit}, agent_type={self.agent_type}, compression_mode={self.compression_mode}")
        
        # If not set token_limit, return original state
        if self.token_limit is None:
            logger.error("[CONTEXT-MANAGER] 🚨 CRITICAL: No token_limit set, the context management doesn't work!")
            return state

        if not isinstance(state, dict) or "messages" not in state:
            logger.error(f"[CONTEXT-MANAGER] 🚨 CRITICAL: Invalid state - type={type(state)}, has_messages={'messages' in state if isinstance(state, dict) else False}")
            return state

        messages = state["messages"]
        logger.info(f"[CONTEXT-MANAGER] 🔍 DEBUG: Found {len(messages)} messages in state")
        
        # Count tokens - try with model if available, otherwise without
        try:
            # Try to get model from state if available
            model = getattr(self, '_model_name', None)
            original_token_count = self.count_tokens(messages, model=model)
        except Exception as e:
            logger.warning(f"[CONTEXT-MANAGER] Failed to count tokens with model, trying without: {e}")
            original_token_count = self.count_tokens(messages)
        
        logger.info(
            f"[CONTEXT-MANAGER] 🔍 DEBUG: Token counting - "
            f"Original token count: {original_token_count:,}, "
            f"Token limit: {self.token_limit:,}, "
            f"Over limit: {original_token_count > self.token_limit}"
        )

        is_over = self.is_over_limit(messages)
        logger.info(f"[CONTEXT-MANAGER] 🔍 DEBUG: is_over_limit returned: {is_over}")
        
        if not is_over:
            # No compression needed, but still return metadata
            logger.info(f"[CONTEXT-MANAGER] 🔍 DEBUG: Messages are within limit, no compression needed")
            state["_context_optimization"] = {
                "compressed": False,
                "original_tokens": original_token_count,
                "compressed_tokens": original_token_count,
                "compression_ratio": 1.0,
                "strategy": self.compression_mode,
                "agent_type": self.agent_type,
                "original_message_count": len(messages),
                "compressed_message_count": len(messages)
            }
            logger.info(f"[CONTEXT-MANAGER] 🔍 DEBUG: Returning metadata (no compression): {state.get('_context_optimization')}")
            return state

        # 2. Compress messages
        logger.info(f"[CONTEXT-MANAGER] 🔍 DEBUG: Messages exceed limit, starting compression with mode: {self.compression_mode}")
        compressed_messages = self._compress_messages(messages)
        
        try:
            compressed_token_count = self.count_tokens(compressed_messages, model=model)
        except Exception as e:
            logger.warning(f"[CONTEXT-MANAGER] Failed to count compressed tokens with model, trying without: {e}")
            compressed_token_count = self.count_tokens(compressed_messages)
        
        # 3. Validate compressed result fits within limit (with retry if needed)
        max_iterations = 3
        iteration = 0
        while compressed_token_count > self.token_limit and iteration < max_iterations:
            logger.warning(
                f"[CONTEXT-MANAGER] ⚠️ Compressed result ({compressed_token_count:,} tokens) "
                f"still exceeds limit ({self.token_limit:,} tokens), applying additional compression (iteration {iteration + 1}/{max_iterations})"
            )
            # Apply more aggressive compression: truncate largest messages
            compressed_messages = self._aggressive_truncate(compressed_messages, self.token_limit)
            try:
                compressed_token_count = self.count_tokens(compressed_messages, model=model)
            except Exception as e:
                logger.warning(f"[CONTEXT-MANAGER] Failed to count tokens after aggressive compression: {e}")
                compressed_token_count = self.count_tokens(compressed_messages)
            iteration += 1
        
        if compressed_token_count > self.token_limit:
            logger.error(
                f"[CONTEXT-MANAGER] 🚨 CRITICAL: Final compressed result ({compressed_token_count:,} tokens) "
                f"still exceeds limit ({self.token_limit:,} tokens) after {max_iterations} iterations. "
                f"This may cause API errors."
            )
        
        compression_ratio = compressed_token_count / original_token_count if original_token_count > 0 else 1.0

        logger.info(
            f"[CONTEXT-MANAGER] 🔍 DEBUG: Message compression completed: {original_token_count:,} -> {compressed_token_count:,} tokens "
            f"(ratio: {compression_ratio:.2%}, strategy: {self.compression_mode}, "
            f"within_limit: {compressed_token_count <= self.token_limit})"
        )

        state["messages"] = compressed_messages
        state["_context_optimization"] = {
            "compressed": True,
            "original_tokens": original_token_count,
            "compressed_tokens": compressed_token_count,
            "token_limit": self.token_limit,
            "within_limit": compressed_token_count <= self.token_limit,
            "compression_ratio": compression_ratio,
            "strategy": self.compression_mode,
            "agent_type": self.agent_type,
            "original_message_count": len(messages),
            "compressed_message_count": len(compressed_messages)
        }
        logger.info(f"[CONTEXT-MANAGER] 🔍 DEBUG: Returning metadata (compressed): {state.get('_context_optimization')}")
        return state

    def _score_message_importance(self, message: BaseMessage, position: int, total: int) -> float:
        """
        Score message importance (0.0 - 1.0).
        
        Based on Cursor/Copilot approach:
        - User queries: Always important (1.0)
        - Errors: Critical (0.9)
        - Final answers/reports: Critical (0.9)
        - Recent messages: Important (0.8)
        - Tool results: Medium (0.5-0.7)
        - Intermediate steps: Low (0.3)
        """
        score = 0.5  # Base score
        
        # Type-based scoring
        if isinstance(message, HumanMessage):
            score = 1.0  # User queries always important
        elif isinstance(message, SystemMessage):
            score = 0.9  # System prompts important
        elif isinstance(message, AIMessage):
            content = str(message.content).lower()
            if any(err in content for err in ["[error]", "error:", "failed", "exception"]):
                score = 0.9  # Errors are critical
            elif hasattr(message, 'name') and message.name in ["reporter", "reflector"]:
                score = 0.9  # Final reports and reflections important
            else:
                score = 0.6  # Regular AI responses
        elif isinstance(message, ToolMessage):
            content_len = len(str(message.content))
            if content_len < 500:
                score = 0.7  # Small tool results often important
            elif content_len < 2000:
                score = 0.5  # Medium results
            else:
                score = 0.4  # Large results can be compressed
        
        # Boost recent messages (last 20% get higher scores)
        recency_threshold = int(total * 0.8)
        if position >= recency_threshold:
            score = min(1.0, score + 0.2)
        
        return score
    
    def _compress_messages(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """
        Compress messages using intelligent strategies.
        
        Strategy depends on compression_mode:
        - 'simple': Original sliding window (keep prefix + recent)
        - 'hierarchical': 3-tier compression (recent full, middle summary, old super-summary)
        - 'importance_based': Score and keep important, summarize rest
        
        Args:
            messages: List of messages to compress

        Returns:
            Compressed message list
        """
        logger.info(f"[CONTEXT-MANAGER] 🔍 DEBUG: _compress_messages called - mode={self.compression_mode}, messages={len(messages)}")
        
        if self.compression_mode == "hierarchical":
            logger.info(f"[CONTEXT-MANAGER] 🔍 DEBUG: Using hierarchical compression")
            result = self._hierarchical_compress(messages)
            logger.info(f"[CONTEXT-MANAGER] 🔍 DEBUG: Hierarchical compression result: {len(result)} messages")
            return result
        elif self.compression_mode == "importance_based":
            logger.info(f"[CONTEXT-MANAGER] 🔍 DEBUG: Using importance-based compression")
            result = self._importance_based_compress(messages)
            logger.info(f"[CONTEXT-MANAGER] 🔍 DEBUG: Importance-based compression result: {len(result)} messages")
            return result
        else:
            # Default: Original simple compression
            logger.info(f"[CONTEXT-MANAGER] 🔍 DEBUG: Using simple compression (default)")
            result = self._simple_compress(messages)
            logger.info(f"[CONTEXT-MANAGER] 🔍 DEBUG: Simple compression result: {len(result)} messages")
            return result
    
    def _simple_compress(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """Original sliding window compression."""
        available_token = self.token_limit
        prefix_messages = []

        # 1. Preserve head messages of specified length to retain system prompts and user input
        for i in range(min(self.preserve_prefix_message_count, len(messages))):
            cur_token_cnt = self._count_message_tokens(messages[i])
            if available_token > 0 and available_token >= cur_token_cnt:
                prefix_messages.append(messages[i])
                available_token -= cur_token_cnt
            elif available_token > 0:
                # Truncate content to fit available tokens
                truncated_message = self._truncate_message_content(
                    messages[i], available_token
                )
                prefix_messages.append(truncated_message)
                return prefix_messages
            else:
                break

        # 2. Compress subsequent messages from the tail, some messages may be discarded
        messages = messages[len(prefix_messages) :]
        suffix_messages = []
        for i in range(len(messages) - 1, -1, -1):
            cur_token_cnt = self._count_message_tokens(messages[i])

            if cur_token_cnt > 0 and available_token >= cur_token_cnt:
                suffix_messages = [messages[i]] + suffix_messages
                available_token -= cur_token_cnt
            elif available_token > 0:
                # Truncate content to fit available tokens
                truncated_message = self._truncate_message_content(
                    messages[i], available_token
                )
                suffix_messages = [truncated_message] + suffix_messages
                return prefix_messages + suffix_messages
            else:
                break

        return prefix_messages + suffix_messages
    
    def _hierarchical_compress(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """
        Hierarchical compression (Claude-style).
        
        Tiers:
        - Tier 1 (Recent): Keep full (last 10 messages)
        - Tier 2 (Middle): Summarize (messages 10-50 back)
        - Tier 3 (Old): Super-summarize (50+ messages back)
        
        Also truncates individual large messages to prevent token overflow.
        """
        # First, truncate individual large messages to prevent overflow
        # Calculate max tokens per message (reserve 20% for overhead, distribute rest)
        max_tokens_per_message = int((self.token_limit * 0.8) / max(len(messages), 1))
        max_chars_per_message = max_tokens_per_message * 4  # ~4 chars per token
        
        truncated_messages = []
        for msg in messages:
            if hasattr(msg, 'content') and isinstance(msg.content, str):
                if len(msg.content) > max_chars_per_message:
                    logger.info(f"[CONTEXT] Truncating large message: {len(msg.content):,} → {max_chars_per_message:,} chars")
                    # Create a copy to avoid modifying original
                    from copy import deepcopy
                    msg_copy = deepcopy(msg)
                    msg_copy.content = msg_copy.content[:max_chars_per_message] + "\n\n... (truncated due to context limit) ..."
                    truncated_messages.append(msg_copy)
                else:
                    truncated_messages.append(msg)
            else:
                truncated_messages.append(msg)
        
        messages = truncated_messages
        
        if len(messages) <= 10:
            return messages  # All recent, no further compression needed
        
        # Separate system prompts (always keep)
        system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
        non_system = [m for m in messages if not isinstance(m, SystemMessage)]
        
        # Tier 1: Recent messages (keep full)
        recent_count = min(10, len(non_system))
        recent = non_system[-recent_count:]
        older = non_system[:-recent_count]
        
        if not older:
            return system_msgs + recent
        
        # Tier 2 & 3: Older messages need summarization
        if len(older) <= 40:
            # Single summary for all older messages
            try:
                summary = self._create_summary_message(older)
                logger.info(f"[CONTEXT] Hierarchical: {len(older)} old messages → 1 summary")
                return system_msgs + [summary] + recent
            except Exception as e:
                logger.error(f"[CONTEXT] Summarization failed: {e}")
                # Fallback: simple truncation
                return system_msgs + older[-20:] + recent
        else:
            # Multi-tier: super-old + middle summaries
            very_old = older[:-40]
            middle = older[-40:]
            
            try:
                super_summary = self._create_summary_message(very_old)
                middle_summary = self._create_summary_message(middle)
                logger.info(f"[CONTEXT] Hierarchical: {len(very_old)} super-old + {len(middle)} middle → 2 summaries")
                return system_msgs + [super_summary, middle_summary] + recent
            except Exception as e:
                logger.error(f"[CONTEXT] Multi-tier summarization failed: {e}")
                # Fallback
                return system_msgs + middle[-20:] + recent
    
    def _importance_based_compress(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """
        Importance-based compression (Cursor-style).
        
        Strategy:
        1. Score all messages by importance
        2. Keep high-importance (score >= 0.7)
        3. Summarize medium-importance (0.4-0.7)
        4. Drop low-importance (< 0.4)
        """
        total = len(messages)
        scored = [(i, msg, self._score_message_importance(msg, i, total)) 
                  for i, msg in enumerate(messages)]
        
        # Always keep system prompts
        system_msgs = [msg for i, msg, score in scored if isinstance(msg, SystemMessage)]
        non_system_scored = [(i, msg, score) for i, msg, score in scored 
                             if not isinstance(msg, SystemMessage)]
        
        # Separate by importance
        high_importance = [msg for i, msg, score in non_system_scored if score >= 0.7]
        medium_importance = [msg for i, msg, score in non_system_scored if 0.4 <= score < 0.7]
        
        logger.info(f"[CONTEXT] Importance: {len(high_importance)} high, {len(medium_importance)} medium")
        
        # Summarize medium-importance messages if there are many
        if len(medium_importance) > 20:
            try:
                medium_summary = self._create_summary_message(medium_importance)
                logger.info(f"[CONTEXT] Summarized {len(medium_importance)} medium-importance messages")
                return system_msgs + [medium_summary] + high_importance
            except Exception as e:
                logger.error(f"[CONTEXT] Importance summarization failed: {e}")
                # Keep some medium messages
                return system_msgs + medium_importance[-10:] + high_importance
        else:
            # Keep all if not too many
            return system_msgs + medium_importance + high_importance

    def _aggressive_truncate(
        self, messages: List[BaseMessage], target_token_limit: int
    ) -> List[BaseMessage]:
        """
        Aggressively truncate messages to fit within token limit.
        Used as fallback when normal compression doesn't reduce enough.
        
        Args:
            messages: List of messages to truncate
            target_token_limit: Target token limit to fit within
            
        Returns:
            Truncated message list
        """
        if not messages:
            return messages
        
        # Calculate current token count
        current_tokens = self.count_tokens(messages)
        if current_tokens <= target_token_limit:
            return messages
        
        # Sort messages by size (largest first) to truncate biggest ones
        message_sizes = [
            (i, self._count_message_tokens(msg)) 
            for i, msg in enumerate(messages)
        ]
        message_sizes.sort(key=lambda x: x[1], reverse=True)
        
        # Calculate how much we need to reduce
        reduction_needed = current_tokens - target_token_limit
        
        truncated_messages = list(messages)
        total_reduced = 0
        
        # Truncate largest messages until we fit
        for msg_idx, msg_tokens in message_sizes:
            if total_reduced >= reduction_needed:
                break
            
            # Calculate how much to truncate from this message
            tokens_to_remove = min(msg_tokens, reduction_needed - total_reduced)
            chars_to_remove = tokens_to_remove * 4  # ~4 chars per token
            
            msg = truncated_messages[msg_idx]
            if hasattr(msg, 'content') and isinstance(msg.content, str):
                # Truncate from the end (preserve beginning)
                new_length = max(0, len(msg.content) - chars_to_remove)
                if new_length < len(msg.content):
                    from copy import deepcopy
                    truncated_msg = deepcopy(msg)
                    truncated_msg.content = truncated_msg.content[:new_length] + "\n\n... (truncated to fit context limit) ..."
                    truncated_messages[msg_idx] = truncated_msg
                    total_reduced += tokens_to_remove
        
        logger.info(
            f"[CONTEXT-MANAGER] Aggressive truncation: {current_tokens:,} -> "
            f"{self.count_tokens(truncated_messages):,} tokens "
            f"(reduced {total_reduced:,} tokens)"
        )
        
        return truncated_messages
    
    def _truncate_message_content(
        self, message: BaseMessage, max_tokens: int
    ) -> BaseMessage:
        """
        Truncate message content while preserving all other attributes by copying the original message
        and only modifying its content attribute.

        Args:
            message: The message to truncate
            max_tokens: Maximum number of tokens to keep

        Returns:
            New message instance with truncated content
        """

        # Create a deep copy of the original message to preserve all attributes
        truncated_message = copy.deepcopy(message)

        # Truncate only the content attribute
        truncated_message.content = message.content[:max_tokens]

        return truncated_message

    def _create_summary_message(self, messages: List[BaseMessage]) -> BaseMessage:
        """
        Create intelligent summary of messages using LLM.
        
        Strategy (inspired by Cursor/Claude):
        1. Group messages by logical chunks
        2. Extract key facts, decisions, actions, errors
        3. Drop verbose intermediate steps
        4. Preserve user intent and critical context

        Args:
            messages: Messages to summarize

        Returns:
            Summary message with compressed context
        """
        if not messages:
            return SystemMessage(content="[No messages to summarize]", name="context_summary")
        
        # Check cache first
        cache_key = hash(tuple(id(m) for m in messages))
        if cache_key in self.summary_cache:
            logger.info("[CONTEXT] Using cached summary")
            return self.summary_cache[cache_key]
        
        try:
            # Format messages for summarization
            formatted_content = self._format_messages_for_summary(messages)
            
            # Create summarization prompt (Cursor-style)
            summary_prompt = f"""Analyze this conversation history and create a concise summary.

**Keep:**
- User intents and questions
- Key findings and data points
- Important decisions and actions taken
- Error messages and issues encountered
- Final results and conclusions

**Drop:**
- Verbose tool outputs (keep only key stats)
- Redundant intermediate steps
- System logs and debug info
- Repetitive confirmations

**Format:** Structured bullet points, max 300 words.

**Conversation History ({len(messages)} messages):**
{formatted_content}

**Summary:**"""

            # Use user's selected model for summarization
            # get_llm_by_type() respects user's model selection from UI via context variables
            from backend.llms.llm import get_llm_by_type
            
            # Use basic model type - will use user's selected model if available
            # Falls back to default (GPT-3.5) if no selection made
            llm = get_llm_by_type("basic")
            logger.info(f"[CONTEXT] Using user's selected model for summarization")
            
            # Generate summary
            from langchain_core.messages import HumanMessage as LCHumanMessage
            response = llm.invoke([LCHumanMessage(content=summary_prompt)])
            summary_text = response.content if hasattr(response, 'content') else str(response)
            
            # Create summary message
            summary_message = SystemMessage(
                content=f"📝 **Previous Context Summary** ({len(messages)} messages compressed):\n\n{summary_text}",
                name="context_summary"
            )
            
            # Cache the summary
            self.summary_cache[cache_key] = summary_message
            
            logger.info(f"[CONTEXT] Created summary: {len(messages)} messages → {len(summary_text)} chars")
            
            return summary_message
            
        except Exception as e:
            logger.error(f"[CONTEXT] Summary generation failed: {e}")
            # Fallback: Create simple text-based summary
            return SystemMessage(
                content=f"📝 Context: {len(messages)} previous messages (summary unavailable)",
                name="context_summary"
            )
    
    def _format_messages_for_summary(self, messages: List[BaseMessage]) -> str:
        """Format messages for LLM summarization."""
        formatted = []
        for i, msg in enumerate(messages[-50:], 1):  # Only last 50 for summarization
            role = "User" if isinstance(msg, HumanMessage) else \
                   "Assistant" if isinstance(msg, AIMessage) else \
                   "System" if isinstance(msg, SystemMessage) else \
                   "Tool"
            
            content = str(msg.content)[:500]  # Truncate very long messages
            if len(str(msg.content)) > 500:
                content += "..."
            
            formatted.append(f"{i}. [{role}] {content}")
        
        return "\n".join(formatted)


def validate_message_content(messages: List[BaseMessage], max_content_length: int = 100000) -> List[BaseMessage]:
    """
    Validate and fix all messages to ensure they have valid content before sending to LLM.
    
    This function ensures:
    1. All messages have a content field
    2. No message has None or empty string content (except for legitimate empty responses)
    3. Complex objects (lists, dicts) are converted to JSON strings
    4. Content is truncated if too long to prevent token overflow
    
    Args:
        messages: List of messages to validate
        max_content_length: Maximum allowed content length per message (default 100000)
    
    Returns:
        List of validated messages with fixed content
    """
    validated = []
    for i, msg in enumerate(messages):
        try:
            # Check if message has content attribute
            if not hasattr(msg, 'content'):
                logger.warning(f"Message {i} ({type(msg).__name__}) has no content attribute")
                msg.content = ""
            
            # Handle None content
            elif msg.content is None:
                logger.warning(f"Message {i} ({type(msg).__name__}) has None content, setting to empty string")
                msg.content = ""
            
            # Handle complex content types (convert to JSON)
            elif isinstance(msg.content, (list, dict)):
                logger.debug(f"Message {i} ({type(msg).__name__}) has complex content type {type(msg.content).__name__}, converting to JSON")
                msg.content = json.dumps(msg.content, ensure_ascii=False)
            
            # Handle other non-string types
            elif not isinstance(msg.content, str):
                logger.debug(f"Message {i} ({type(msg).__name__}) has non-string content type {type(msg.content).__name__}, converting to string")
                msg.content = str(msg.content)
            
            # Validate content length
            if isinstance(msg.content, str) and len(msg.content) > max_content_length:
                logger.warning(f"Message {i} content truncated from {len(msg.content)} to {max_content_length} chars")
                msg.content = msg.content[:max_content_length].rstrip() + "..."
            
            validated.append(msg)
        except Exception as e:
            logger.error(f"Error validating message {i}: {e}")
            # Create a safe fallback message
            if isinstance(msg, ToolMessage):
                msg.content = json.dumps({"error": str(e)}, ensure_ascii=False)
            else:
                msg.content = f"[Error processing message: {str(e)}]"
            validated.append(msg)
    
    return validated
