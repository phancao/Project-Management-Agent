// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { resolveServiceURL } from "./resolve-service-url";

export interface AIProviderAPIKey {
  id: string;
  provider_id: string;
  provider_name: string;
  api_key?: string; // Masked (shows only last 4 chars)
  base_url?: string;
  model_name?: string;
  additional_config?: Record<string, unknown>;
  is_active: boolean;
  has_api_key: boolean;
  created_at: string;
  updated_at: string;
}

export interface AIProviderAPIKeyRequest {
  provider_id: string;
  provider_name: string;
  api_key?: string;
  base_url?: string;
  model_name?: string;
  additional_config?: Record<string, unknown>;
  is_active?: boolean;
}

export async function listAIProviders(): Promise<AIProviderAPIKey[]> {
  const url = resolveServiceURL("ai/providers");
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
      let errorMessage = "Failed to fetch AI providers";
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
      throw new Error("Invalid response format: expected an array of AI providers");
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

export async function saveAIProvider(
  request: AIProviderAPIKeyRequest,
): Promise<AIProviderAPIKey> {
  const url = resolveServiceURL("ai/providers");
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to save AI provider" }));
    throw new Error(error.detail || "Failed to save AI provider");
  }

  return response.json();
}

export async function deleteAIProvider(provider_id: string): Promise<void> {
  const url = resolveServiceURL(`ai/providers/${provider_id}`);
  const response = await fetch(url, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to delete AI provider" }));
    throw new Error(error.detail || "Failed to delete AI provider");
  }
}

