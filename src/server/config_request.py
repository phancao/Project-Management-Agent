# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.server.rag_request import RAGConfigResponse


class ModelProviderInfo(BaseModel):
    """Information about a model provider."""
    id: str = Field(..., description="Provider ID")
    name: str = Field(..., description="Provider name")
    description: str = Field(..., description="Provider description")
    icon: str = Field(..., description="Provider icon")
    models: List[str] = Field(..., description="Available models")
    requires_api_key: bool = Field(True, description="Whether API key is required")
    supports_streaming: bool = Field(True, description="Whether streaming is supported")


class ConfigResponse(BaseModel):
    """Response model for server config."""

    rag: RAGConfigResponse = Field(..., description="The config of the RAG")
    models: dict[str, list[str]] = Field(..., description="The configured models")
    providers: Optional[List[Dict[str, Any]]] = Field(None, description="Available model providers")
