"use client";

/**
 * Auto-configure PM MCP Server on mount
 * This component should be included in the root layout or app component
 */

import { useEffect } from "react";
import { autoConfigurePMMCPServer } from "~/core/mcp/auto-config";

export function PMMCPAutoConfig() {
  useEffect(() => {
    // Auto-configure PM MCP server on mount
    void autoConfigurePMMCPServer();

    // Check periodically (every 5 minutes)
    const interval = setInterval(() => {
      void autoConfigurePMMCPServer();
    }, 5 * 60 * 1000); // 5 minutes

    return () => clearInterval(interval);
  }, []);

  return null; // This component doesn't render anything
}

