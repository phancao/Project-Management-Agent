/**
 * Auto-configuration for PM MCP Server
 * 
 * Automatically detects and configures PM MCP Server if available.
 */

import { queryMCPServerMetadata } from "../api/mcp";
import type { MCPServerMetadata, SimpleStdioMCPServerMetadata, SimpleSSEMCPServerMetadata } from "../mcp";
import { useSettingsStore, saveSettings } from "../store/settings-store";

const PM_MCP_SERVER_URL = "http://localhost:8080";
const PM_MCP_SERVER_NAME = "pm-server";

/**
 * Check if PM MCP server is available at default URL
 */
export async function checkPMMCPServerAvailable(): Promise<boolean> {
  try {
    const response = await fetch(`${PM_MCP_SERVER_URL}/health`, {
      method: "GET",
      signal: AbortSignal.timeout(5000), // 5 second timeout
    });
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * Auto-configure PM MCP server if available and not already configured
 * 
 * Note: PM MCP server is auto-injected by the backend for PM chat endpoints.
 * This frontend auto-config is mainly for UI display purposes.
 * If the server is already configured or auto-injection fails, we skip configuration.
 */
export async function autoConfigurePMMCPServer(): Promise<MCPServerMetadata | null> {
  // Check if already configured
  const currentSettings = useSettingsStore.getState();
  const existingPMServer = currentSettings.mcp.servers.find(
    (server) => server.name === PM_MCP_SERVER_NAME || server.name.includes("pm")
  );

  if (existingPMServer) {
    return existingPMServer;
  }

  // Try SSE transport first (Docker mode), fallback to stdio (local development)
  try {
    // Check if server is available via SSE (Docker)
    const isAvailable = await checkPMMCPServerAvailable();

    if (isAvailable) {
      // Server is running in Docker with SSE transport

      try {
        // Query metadata via SSE transport with internal auth header
        const sseConfig: SimpleSSEMCPServerMetadata = {
          transport: "sse",
          name: PM_MCP_SERVER_NAME,
          url: `${PM_MCP_SERVER_URL}/sse`,
          headers: {
            "X-User-ID": "internal-frontend", // Bypass API key auth for internal use
          },
        };

        const metadata = await queryMCPServerMetadata(
          sseConfig,
          AbortSignal.timeout(60000) // 60 second timeout
        );

        // Create PM MCP server configuration with SSE transport
        const pmServer: MCPServerMetadata = {
          ...metadata,
          name: PM_MCP_SERVER_NAME,
          transport: "sse",
          url: `${PM_MCP_SERVER_URL}/sse`,
          enabled: true,
          createdAt: Date.now(),
          updatedAt: Date.now(),
        };

        // Add to settings
        const updatedServers = [...currentSettings.mcp.servers, pmServer];
        useSettingsStore.setState({
          mcp: {
            servers: updatedServers,
          },
        });

        // Save to localStorage
        saveSettings();


        return pmServer;
      } catch (sseError) {
        console.warn("[PM MCP] SSE configuration failed:", sseError);
        // PM MCP server is auto-injected by the backend for PM chat endpoints
        // No stdio fallback needed - it doesn't work in Docker anyway
        return null;
      }
    }

    // Server not available via SSE health check
    console.log("[PM MCP] Server not available at", PM_MCP_SERVER_URL);
    // Backend will auto-inject MCP server for PM chat endpoints
    return null;
  } catch (error) {
    console.error("[PM MCP] Failed to auto-configure:", error);
    // Backend will still auto-inject for PM chat endpoints
    return null;
  }
}

/**
 * Hook to auto-configure PM MCP server on mount
 * Use this in your app component or root layout
 */
export function useAutoConfigurePMMCP() {
  if (typeof window === "undefined") {
    return;
  }

  // Check on mount and periodically (every 5 minutes)
  void autoConfigurePMMCPServer();

  const interval = setInterval(() => {
    void autoConfigurePMMCPServer();
  }, 5 * 60 * 1000); // 5 minutes

  // Cleanup on unmount
  return () => clearInterval(interval);
}

