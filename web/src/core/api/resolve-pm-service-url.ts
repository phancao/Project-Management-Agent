import { env } from "~/env";

export function resolvePMServiceURL(path: string) {
    // PM Service REST API is running on port 8001 with prefix /api/v1
    // We prioritize an explicit env var, then fallback to direct localhost:8001
    // Use Next.js API Proxy to reach PM Service via internal Docker network
    // This avoids CORS and browser connectivity issues with direct port access
    let baseUrl = "/api/pm-service/";

    // If on server, we might need absolute URL, but usually hooks run on client.
    // Falls back to relative path for browser.

    // Note: The previous direct 8001 access was unreliable.

    // Remove leading slash from path if present
    if (path.startsWith('/')) {
        path = path.slice(1);
    }

    return `${baseUrl}${path}`;
}
