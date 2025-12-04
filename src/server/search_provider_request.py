# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from typing import Optional
from pydantic import BaseModel, Field


class SearchProviderAPIKeyRequest(BaseModel):
    """Request model for search provider API key."""
    provider_id: str = Field(..., description="Provider ID (e.g., 'tavily', 'brave_search', 'duckduckgo')")
    provider_name: str = Field(..., description="Provider display name")
    api_key: Optional[str] = Field(None, description="API key (will be masked in responses)")
    base_url: Optional[str] = Field(None, description="Optional custom base URL (e.g., for Searx)")
    additional_config: Optional[dict] = Field(None, description="Additional provider-specific config")
    is_active: bool = Field(True, description="Whether the provider is active")
    is_default: bool = Field(False, description="Whether this is the default provider")


class SearchProviderAPIKeyResponse(BaseModel):
    """Response model for search provider API key."""
    id: str
    provider_id: str
    provider_name: str
    api_key: Optional[str] = Field(None, description="Masked API key (shows only last 4 chars)")
    base_url: Optional[str] = None
    additional_config: Optional[dict] = None
    is_active: bool
    is_default: bool
    has_api_key: bool = Field(..., description="Whether an API key is set (without revealing it)")
    created_at: str
    updated_at: str

