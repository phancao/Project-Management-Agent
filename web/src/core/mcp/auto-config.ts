/**
 * Auto-configuration for PM MCP Server
 * 
 * Automatically detects and configures PM MCP Server if available.
 */

import type { MCPServerMetadata, SimpleStdioMCPServerMetadata } from "../mcp";
import { queryMCPServerMetadata } from "../api/mcp";
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
      signal: AbortSignal.timeout(3000), // 3 second timeout
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
    console.log("[PM MCP] Server already configured:", existingPMServer.name);
    return existingPMServer;
  }

  // PM MCP server is auto-injected by the backend for PM chat
  // Frontend doesn't need to configure it separately
  // Skip auto-configuration to avoid errors
  console.log("[PM MCP] Skipping auto-configuration - server is auto-injected by backend");
  return null;

  // NOTE: The code below is kept for reference but disabled
  // If you want to enable frontend auto-config, uncomment and ensure the server is running
  /*
  try {
    // Query server metadata using stdio transport
    // PM MCP server runs via stdio, not SSE
    const serverConfig: SimpleStdioMCPServerMetadata = {
      transport: "stdio",
      name: PM_MCP_SERVER_NAME,
      command: "python3",
      args: [
        "scripts/run_pm_mcp_server.py",
        "--transport",
        "stdio",
      ],
    };
    
    const metadata = await queryMCPServerMetadata(
      serverConfig,
      AbortSignal.timeout(10000) // 10 second timeout
    );

    // Create PM MCP server configuration
    const pmServer: MCPServerMetadata = {
      ...metadata,
      name: PM_MCP_SERVER_NAME,
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

    console.log("[PM MCP] Auto-configured:", pmServer.name);
    console.log(`[PM MCP] Tools available: ${pmServer.tools.length}`);

    return pmServer;
  } catch (error) {
    console.error("[PM MCP] Failed to auto-configure:", error);
    return null;
  }
  */
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

