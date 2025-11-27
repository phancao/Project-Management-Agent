// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { resolveServiceURL } from "../resolve-service-url";

export interface ProviderConfig {
  id?: string;
  provider_type: "openproject" | "openproject_v13" | "jira" | "clickup";
  base_url: string;
  api_key?: string;
  api_token?: string;
  username?: string;
  organization_id?: string;
  workspace_id?: string;
  // MCP Server provider ID - used for AI Agent context
  mcp_provider_id?: string;
}

export interface ProjectImportRequest {
  provider_type: string;
  base_url: string;
  api_key?: string;
  api_token?: string;
  username?: string;
  organization_id?: string;
  workspace_id?: string;
  import_options?: {
    skip_existing?: boolean;
    auto_sync?: boolean;
  };
}

export interface ProjectInfo {
  id: string;
  name: string;
  description?: string;
  status?: string;
}

export interface ProjectImportResponse {
  success: boolean;
  provider_config_id?: string;
  total_projects: number;
  projects: ProjectInfo[];
  errors: Array<{ error: string; type?: string }>;
  message?: string;
  // MCP sync result
  mcp_sync?: {
    success: boolean;
    mcp_provider_id?: string;
    error?: string;
  };
}

export async function importProjectsFromProvider(
  request: ProjectImportRequest,
): Promise<ProjectImportResponse> {
  const response = await fetch(
    resolveServiceURL("pm/providers/import-projects"),
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to save provider configuration");
  }

  return response.json();
}

export async function listProviders(): Promise<ProviderConfig[]> {
  const url = resolveServiceURL("pm/providers");
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000);
  
  try {
    const response = await fetch(url, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      cache: 'no-store',
    });
    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorMessage = "Failed to fetch providers";
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
      throw new Error("Invalid response format: expected an array of providers");
    }
    
    // Map and filter in one pass for better performance
    return data
      .filter((p: any): p is any => p?.id && p?.provider_type)
      .map((p: any): ProviderConfig => ({
        id: p.id,
        provider_type: p.provider_type,
        base_url: p.base_url || '',
        username: p.username,
        organization_id: p.organization_id,
        workspace_id: p.workspace_id,
        // Include MCP provider ID for AI Agent context
        mcp_provider_id: p.mcp_provider_id,
      }));
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

export async function getProviderTypes(): Promise<
  Array<{ type: string; display_name: string }>
> {
  const response = await fetch(resolveServiceURL("pm/providers/types"), {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error("Failed to fetch provider types");
  }

  return response.json();
}

export async function getProviderProjects(
  providerId: string,
): Promise<{ success: boolean; total_projects: number; projects: ProjectInfo[] }> {
  const response = await fetch(
    resolveServiceURL(`pm/providers/${providerId}/projects`),
    {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    },
  );

  if (!response.ok) {
    let errorMessage = "Failed to fetch projects";
    try {
      const error = await response.json();
      // Extract error message from various possible formats
      errorMessage = error.detail || error.message || error.error || errorMessage;
      
      // For 403 errors, provide more context
      if (response.status === 403) {
        if (errorMessage.includes("forbidden") || errorMessage.includes("permission")) {
          // Use the detailed message from backend
        } else {
          errorMessage = "Access forbidden. The API token may not have permission to list projects, or the account doesn't have access to any projects. Please check your provider permissions.";
        }
      }
    } catch {
      // If response is not JSON, use status code
      if (response.status === 403) {
        errorMessage = "Access forbidden. The API token may not have permission to list projects, or the account doesn't have access to any projects. Please check your provider permissions.";
      } else if (response.status === 401) {
        errorMessage = "Authentication failed. Please check your API key/token.";
      } else {
        errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      }
    }
    throw new Error(errorMessage);
  }

  const data = await response.json();
  
  // Backend returns either an array (old format) or an object (new format)
  if (Array.isArray(data)) {
    // Old format: array of projects
    return {
      success: true,
      total_projects: data.length,
      projects: data,
    };
  } else if (data && typeof data === 'object') {
    // New format: object with success, total_projects, projects
    return {
      success: data.success !== false, // Default to true if not specified
      total_projects: data.total_projects || data.projects?.length || 0,
      projects: data.projects || [],
    };
  }
  
  // Fallback: empty result
  return {
    success: true,
    total_projects: 0,
    projects: [],
  };
}

export async function updateProvider(
  providerId: string,
  request: ProjectImportRequest,
): Promise<ProviderConfig> {
  const response = await fetch(
    resolveServiceURL(`pm/providers/${providerId}`),
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to update provider");
  }

  return response.json();
}

export async function testProviderConnection(
  request: ProjectImportRequest,
): Promise<{ success: boolean; message: string }> {
  const response = await fetch(
    resolveServiceURL("pm/providers/test-connection"),
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Connection test failed");
  }

  return response.json();
}

export async function deleteProvider(providerId: string): Promise<void> {
  const response = await fetch(
    resolveServiceURL(`pm/providers/${providerId}`),
    {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to delete provider");
  }
}
