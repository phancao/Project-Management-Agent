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
  console.log('[listProviders] Fetching providers from:', url);
  console.log('[listProviders] Full URL details:', {
    url,
    protocol: new URL(url).protocol,
    hostname: new URL(url).hostname,
    port: new URL(url).port,
  });
  
  // Create AbortController for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => {
    console.error('[listProviders] Request timeout after 15 seconds, aborting...');
    controller.abort();
  }, 15000); // 15 second timeout
  
  let response: Response;
  try {
    const startTime = Date.now();
    console.log('[listProviders] Starting fetch at', new Date().toISOString());
    response = await fetch(url, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
      signal: controller.signal,
      // Add cache control to prevent caching issues
      cache: 'no-store',
    });
    clearTimeout(timeoutId);
    const duration = Date.now() - startTime;
    console.log('[listProviders] Fetch completed in', duration, 'ms, status:', response.status);
    console.log('[listProviders] Response headers:', Object.fromEntries(response.headers.entries()));
  } catch (error) {
    clearTimeout(timeoutId);
    // Catch network errors (connection refused, timeout, etc.)
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error('[listProviders] Network error:', errorMessage, error);
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error(`Request timeout: Failed to fetch providers within 15 seconds. The backend server may be slow or unresponsive.`);
    }
    throw new Error(`Network error: ${errorMessage}. Please check if the backend server is running at ${url}`);
  }

  if (!response.ok) {
    // Extract error detail from backend response
    let errorMessage = "Failed to fetch providers";
    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorMessage;
    } catch {
      // If response is not JSON, use status text
      errorMessage = response.statusText || errorMessage;
    }
    
    // Throw error with detailed message so it can be displayed to user
    throw new Error(errorMessage);
  }

  let data: any;
  try {
    data = await response.json();
    console.log('[listProviders] Raw API response:', data);
  } catch (error) {
    console.error('[listProviders] Failed to parse JSON:', error);
    throw new Error("Failed to parse response from server. The response may not be valid JSON.");
  }
  
  // Map database response to ProviderConfig format
  // Note: API keys/tokens are not returned for security
  // When loading projects, we'll need to use the saved provider's credentials
  if (!Array.isArray(data)) {
    console.error('[listProviders] Invalid response format, expected array, got:', typeof data, data);
    throw new Error("Invalid response format: expected an array of providers");
  }
  
  const mappedProviders: (ProviderConfig | null)[] = data.map((p: any) => {
    if (!p || !p.id || !p.provider_type) {
      console.warn("[listProviders] Invalid provider data:", p);
      return null;
    }
    return {
      id: p.id,
      provider_type: p.provider_type,
      base_url: p.base_url || '',
      username: p.username || null,
      organization_id: p.organization_id || null,
      workspace_id: p.workspace_id || null,
      // api_key and api_token are not returned from list endpoint for security
      // They will be retrieved when needed for project loading
    };
  });
  
  const mapped: ProviderConfig[] = mappedProviders.filter(
    (p): p is ProviderConfig => p !== null
  );
  
  console.log('[listProviders] Mapped providers:', mapped);
  return mapped;
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
  
  // Backend returns an array, wrap it in the expected format
  const projectsArray = Array.isArray(data) ? data : [];
  return {
    success: true,
    total_projects: projectsArray.length,
    projects: projectsArray,
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
