// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

/**
 * Get backend URL for server-side API routes.
 * 
 * In Docker, server-side Next.js API routes should use the Docker service name
 * to connect to the backend. The browser (client-side) uses NEXT_PUBLIC_API_URL
 * which is set to localhost:8000.
 */
export function getBackendUrl(): string {
  // For server-side (Next.js API routes running in Docker), use Docker service name
  // Check if we're running in Docker by checking if the service name resolves
  // In Docker Compose, services can reach each other by service name
  // Try to use Docker service name first (for server-side API routes)
  const dockerServiceUrl = 'http://api:8000';
  
  // For server-side API routes, prefer Docker service name
  // This works because Next.js API routes run on the server (Node.js), not in the browser
  // Client-side code (browser) will use NEXT_PUBLIC_API_URL which should be localhost:8000
  const serverUrl = process.env.BACKEND_URL ?? process.env.API_URL;
  if (serverUrl) {
    return serverUrl.replace(/\/api\/?$/, '');
  }
  
  // Use Docker service name for server-side requests (Next.js API routes)
  // The browser will use NEXT_PUBLIC_API_URL which is set to localhost:8000
  return dockerServiceUrl;
}

