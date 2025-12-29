# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

# Standard library imports
from typing import Any, Dict, Iterator, List, Mapping, Optional, Type, Union

# Third-party imports
import openai
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.messages import (
    AIMessageChunk,
    BaseMessage,
    BaseMessageChunk,
    ChatMessageChunk,
    FunctionMessageChunk,
    HumanMessageChunk,
    SystemMessageChunk,
    ToolMessageChunk,
)
from langchain_core.messages.ai import UsageMetadata
from langchain_core.messages.tool import tool_call_chunk
from langchain_core.outputs import ChatGenerationChunk, ChatResult
from langchain_openai import ChatOpenAI
from langchain_openai.chat_models.base import (
    _create_usage_metadata,
    _handle_openai_bad_request,
    warnings,
)


def _convert_delta_to_message_chunk(
    delta_dict: Mapping[str, Any], default_class: Type[BaseMessageChunk]
) -> BaseMessageChunk:
    """Convert a delta dictionary to a message chunk, handling reasoning_content."""
    import logging
    logger = logging.getLogger(__name__)
    
    content = delta_dict.get("content", "") or ""
    role = delta_dict.get("role")
    message_id = delta_dict.get("id")
    additional_kwargs: Dict[str, Any] = {}

    # DEBUG: Log delta_dict keys to see what's available (always log for debugging)
    delta_keys = list(delta_dict.keys()) if delta_dict else []

    # Extract tool calls if present
    tool_call_chunks = []
    if "tool_calls" in delta_dict and delta_dict["tool_calls"] is not None:
        for tool_call in delta_dict["tool_calls"]:
            tool_call_chunks.append(
                tool_call_chunk(
                    name=tool_call.get("function", {}).get("name", ""),
                    args=tool_call.get("function", {}).get("arguments", ""),
                    id=tool_call.get("id"),
                    index=tool_call.get("index"),
                )
            )

    # Handle reasoning content for OpenAI reasoning models (o1/o3)
    # Check both "reasoning_content" and nested structures
    reasoning_content = None
    if "reasoning_content" in delta_dict:
        reasoning_content = delta_dict.get("reasoning_content")
        if reasoning_content:
            additional_kwargs["reasoning_content"] = reasoning_content
        pass

    # Return appropriate message chunk based on role
    if role == "user" or default_class == HumanMessageChunk:
        return HumanMessageChunk(content=content, id=message_id)
    elif role == "assistant" or default_class == AIMessageChunk:
        return AIMessageChunk(
            content=content,
            additional_kwargs=additional_kwargs,
            id=message_id,
            tool_call_chunks=tool_call_chunks,  # type: ignore[arg-type]
        )
    elif role in ("system", "developer") or default_class == SystemMessageChunk:
        if role == "developer":
            additional_kwargs = {"__openai_role__": "developer"}
        return SystemMessageChunk(
            content=content, id=message_id, additional_kwargs=additional_kwargs
        )
    elif role == "function" or default_class == FunctionMessageChunk:
        function_name = delta_dict.get("name", "")
        return FunctionMessageChunk(content=content, name=function_name, id=message_id)
    elif role == "tool" or default_class == ToolMessageChunk:
        tool_call_id = delta_dict.get("tool_call_id", "")
        return ToolMessageChunk(
            content=content, tool_call_id=tool_call_id, id=message_id
        )
    elif role or default_class == ChatMessageChunk:
        return ChatMessageChunk(content=content, role=role, id=message_id)
    else:
        return default_class(content=content, id=message_id)  # type: ignore


def _convert_chunk_to_generation_chunk(
    chunk: Dict[str, Any],
    default_chunk_class: Type[BaseMessageChunk],
    base_generation_info: Optional[Dict[str, Any]],
) -> Optional[ChatGenerationChunk]:
    """Convert a chunk dictionary to a ChatGenerationChunk, handling reasoning_content."""
    import logging
    logger = logging.getLogger(__name__)
    
    # DEBUG: Log chunk structure to see what we're receiving
    chunk_type = chunk.get("type")
    chunk_keys = list(chunk.keys())
    
    # DEBUG: Check for reasoning_text events (OpenAI's format for reasoning)
    # OpenAI uses response.reasoning_text.done events for reasoning content
    if chunk_type == "response.reasoning_text.done":
        reasoning_text = chunk.get("text", "")
        # Create a special chunk with reasoning content
        if reasoning_text:
            additional_kwargs = {"reasoning_content": reasoning_text}
            message_chunk = AIMessageChunk(
                content="",
                additional_kwargs=additional_kwargs,
            )
            return ChatGenerationChunk(message=message_chunk, generation_info=base_generation_info or None)
    
    # Skip content.delta type chunks from beta.chat.completions.stream
    if chunk_type == "content.delta":
        return None

    choices = (
        chunk.get("choices", [])
        # Handle chunks from beta.chat.completions.stream format
        or chunk.get("chunk", {}).get("choices", [])
    )

    # Handle empty choices
    if not choices:
        return None

    choice = choices[0]
    delta = choice.get("delta", {})
    
    if delta is None:
        return None

    finish_reason = choice.get("finish_reason")

    # Convert delta to message chunk (this will extract reasoning_content from delta)
    message_chunk = _convert_delta_to_message_chunk(delta, default_chunk_class)

    generation_info = dict(base_generation_info) if base_generation_info else {}
    
    if finish_reason:
        generation_info["finish_reason"] = finish_reason
        if model_name := chunk.get("model"):
            generation_info["model_name"] = model_name
        if system_fingerprint := chunk.get("system_fingerprint"):
            generation_info["system_fingerprint"] = system_fingerprint

    # Handle usage metadata
    if "usage" in chunk and chunk["usage"] is not None:
        usage_metadata = _create_usage_metadata(chunk["usage"])
        if usage_metadata and isinstance(message_chunk, AIMessageChunk):
            message_chunk.usage_metadata = usage_metadata

    return ChatGenerationChunk(message=message_chunk, generation_info=generation_info or None)


class ChatOpenAIReasoning(ChatOpenAI):
    """Extended ChatOpenAI model with reasoning capabilities for o1/o3 models.

    This class extends the base ChatOpenAI model to support OpenAI's reasoning models
    (o1-preview, o1-mini, o1, o3-mini, o3) that include reasoning_content in their responses.
    It handles the extraction and preservation of reasoning content during both streaming
    and non-streaming operations.
    """
    
    def __init__(self, **kwargs):
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[ChatOpenAIReasoning] Initializing with model={kwargs.get('model')}")
        super().__init__(**kwargs)

    def _create_chat_result(
        self,
        response: Union[Dict[str, Any], openai.BaseModel],
        generation_info: Optional[Dict[str, Any]] = None,
    ) -> ChatResult:
        """Create a chat result from the OpenAI response.

        Args:
            response: The response from OpenAI API
            generation_info: Additional generation information

        Returns:
            ChatResult: The formatted chat result with reasoning content if available
        """
        chat_result = super()._create_chat_result(response, generation_info)

        # Only process BaseModel responses (not raw dict responses)
        if not isinstance(response, openai.BaseModel):
            return chat_result

        # Extract reasoning content if available
        try:
            if (
                hasattr(response, "choices")
                and response.choices
                and hasattr(response.choices[0], "message")
                and hasattr(response.choices[0].message, "reasoning_content")
            ):
                reasoning_content = response.choices[0].message.reasoning_content
                if reasoning_content and chat_result.generations:
                    chat_result.generations[0].message.additional_kwargs[
                        "reasoning_content"
                    ] = reasoning_content
        except (IndexError, AttributeError):
            # If reasoning content extraction fails, continue without it
            pass

        return chat_result

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        """Create a streaming generator for chat completions with reasoning_content support.

        Args:
            messages: List of messages to send to the model
            stop: Optional list of stop sequences
            run_manager: Optional callback manager for LLM runs
            **kwargs: Additional keyword arguments for the API call

        Yields:
            ChatGenerationChunk: Individual chunks from the streaming response with reasoning_content
        """
        kwargs["stream"] = True
        payload = self._get_request_payload(messages, stop=stop, **kwargs)
        default_chunk_class: Type[BaseMessageChunk] = AIMessageChunk
        base_generation_info: Dict[str, Any] = {}

        # Handle response format for beta completions
        if "response_format" in payload:
            if self.include_response_headers:
                warnings.warn(
                    "Cannot currently include response headers when response_format is "
                    "specified."
                )
            payload.pop("stream")
            response_stream = self.root_client.beta.chat.completions.stream(**payload)
            context_manager = response_stream
        else:
            # Handle regular streaming with optional response headers
            if self.include_response_headers:
                raw_response = self.client.with_raw_response.create(**payload)
                response = raw_response.parse()
                base_generation_info = {"headers": dict(raw_response.headers)}
            else:
                response = self.client.create(**payload)
            context_manager = response

        try:
            with context_manager as response:
                is_first_chunk = True
                for chunk in response:
                    # Convert chunk to dict if it's a model object
                    if not isinstance(chunk, dict):
                        chunk = chunk.model_dump()
                    
                    # DEBUG: Log raw chunk before processing
                    import logging
                    logger = logging.getLogger(__name__)
                    if chunk_type_raw or "reasoning" in str(chunk).lower():
                        pass

                    generation_chunk = _convert_chunk_to_generation_chunk(
                        chunk,
                        default_chunk_class,
                        base_generation_info if is_first_chunk else {},
                    )

                    if generation_chunk is None:
                        continue

                    # Update default chunk class for subsequent chunks
                    default_chunk_class = generation_chunk.message.__class__

                    # Handle log probabilities for callback
                    logprobs = (generation_chunk.generation_info or {}).get("logprobs")
                    if run_manager:
                        run_manager.on_llm_new_token(
                            generation_chunk.text,
                            chunk=generation_chunk,
                            logprobs=logprobs,
                        )

                    is_first_chunk = False
                    yield generation_chunk

        except openai.BadRequestError as e:
            _handle_openai_bad_request(e)

        # Handle final completion for response_format requests
        if hasattr(response, "get_final_completion") and "response_format" in payload:
            try:
                final_completion = response.get_final_completion()
                generation_chunk = self._get_generation_chunk_from_completion(
                    final_completion
                )
                if run_manager:
                    run_manager.on_llm_new_token(
                        generation_chunk.text, chunk=generation_chunk
                    )
                yield generation_chunk
            except AttributeError:
                # If get_final_completion method doesn't exist, continue without it
                pass

