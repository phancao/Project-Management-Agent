// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { resolveServiceURL } from "./resolve-service-url";

export interface SearchProviderConfig {
  id: string;
  provider_id: string;
  provider_name: string;
  api_key?: string;
  base_url?: string;
  additional_config?: Record<string, any>;
  is_active: boolean;
  is_default: boolean;
  has_api_key: boolean;
  created_at: string;
  updated_at: string;
}

export interface SearchProviderRequest {
  provider_id: string;
  provider_name: string;
  api_key?: string;
  base_url?: string;
  additional_config?: Record<string, any>;
  is_active?: boolean;
  is_default?: boolean;
}

export async function listSearchProviders(): Promise<SearchProviderConfig[]> {
  const url = resolveServiceURL("search/providers");
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000); // 15 second timeout
  
  try {
    const response = await fetch(url, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
      signal: controller.signal,
    });
    
    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorMessage = "Failed to fetch search providers";
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorMessage;
      } catch {
        errorMessage = response.statusText || errorMessage;
      }
      throw new Error(errorMessage);
    }

    const data = await response.json();
    
    if (!Array.isArray(data)) {
      throw new Error("Invalid response format: expected an array of search providers");
    }
    
    return data;
  } catch (error) {
    clearTimeout(timeoutId);
    
    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new Error('Request timeout: Failed to fetch providers within 15 seconds. The backend server may be slow or unresponsive.');
      }
      if (error.message.startsWith('Request timeout') || error.message.startsWith('Invalid response format')) {
        throw error; // Re-throw already formatted errors
      }
      throw new Error(`Network error: ${error.message}. Please check if the backend server is running at ${url}`);
    }
    throw new Error(`Network error: ${String(error)}. Please check if the backend server is running at ${url}`);
  }
}

export async function saveSearchProvider(
  request: SearchProviderRequest
): Promise<SearchProviderConfig> {
  const url = resolveServiceURL("search/providers");
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to save search provider" }));
    throw new Error(error.detail || "Failed to save search provider");
  }

  return response.json();
}

export async function deleteSearchProvider(providerId: string): Promise<void> {
  const url = resolveServiceURL(`search/providers/${providerId}`);
  const response = await fetch(url, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to delete search provider" }));
    throw new Error(error.detail || "Failed to delete search provider");
  }
}

export async function testSearchProviderConnection(
  request: SearchProviderRequest
): Promise<{ success: boolean; message: string }> {
  const url = resolveServiceURL("search/providers/test-connection");
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Connection test failed" }));
    throw new Error(error.detail || "Connection test failed");
  }

  return response.json();
}

