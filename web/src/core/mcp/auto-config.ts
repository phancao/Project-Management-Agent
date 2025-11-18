/**
 * Auto-configuration for PM MCP Server
 * 
 * Automatically detects and configures PM MCP Server if available.
 */

import type { MCPServerMetadata, SimpleSSEMCPServerMetadata } from "../mcp";
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

  // Check if server is available
  const isAvailable = await checkPMMCPServerAvailable();
  if (!isAvailable) {
    console.log("[PM MCP] Server not available at", PM_MCP_SERVER_URL);
    return null;
  }

  try {
    // Query server metadata
    const serverConfig: SimpleSSEMCPServerMetadata = {
      transport: "sse",
      name: PM_MCP_SERVER_NAME,
      url: PM_MCP_SERVER_URL,
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

