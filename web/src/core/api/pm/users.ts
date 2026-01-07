import { resolvePMServiceURL } from "~/core/api/resolve-pm-service-url";

export interface PMUser {
    id: string;          // Composite ID: "providerUUID:userId" (e.g., "6a97081f-...:335")
    shortId: string;     // Just the numeric/short part (e.g., "335") - for filtering tasks/time
    name: string;
    email: string;
    avatar?: string;
    roles?: string[];
}

/**
 * Extract the short ID from a composite ID.
 * E.g., "6a97081f-7e78-46f0-afc1-6be1bd5f21c7:335" -> "335"
 * If no colon, returns the ID as-is.
 */
export function extractShortId(compositeId: string): string {
    const parts = compositeId.split(':');
    return parts.length > 1 ? (parts[parts.length - 1] ?? compositeId) : compositeId;
}

/**
 * Check if a user ID matches (handles both composite and short formats)
 */
export function matchesUserId(userId: string, targetId: string): boolean {
    if (userId === targetId) return true;
    return extractShortId(userId) === extractShortId(targetId);
}

export async function listUsers(projectId?: string): Promise<PMUser[]> {
    console.log('[DEBUG API] listUsers called - projectId:', projectId);
    let url = resolvePMServiceURL("users");

    if (projectId) {
        const params = new URLSearchParams();
        params.append("project_id", projectId);
        url = `${url}?${params.toString()}`;
    }

    const response = await fetch(url, {
        method: "GET",
        headers: {
            "Content-Type": "application/json",
        },
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to list users");
    }

    // Backend returns { items: [], total: ... } 
    // We need to check the shape. Based on other clients/routers, it returns ListResponse
    const data = await response.json();
    // Add shortId to each user
    return (data.items || []).map((user: Omit<PMUser, 'shortId'>) => ({
        ...user,
        shortId: extractShortId(user.id),
    }));
}

/**
 * Fetch a single user by ID.
 * Returns null if user not found (instead of throwing).
 */
export async function getUser(userId: string): Promise<PMUser | null> {
    console.log('[DEBUG API] getUser called - userId:', userId);
    const url = resolvePMServiceURL(`users/${userId}`);

    const response = await fetch(url, {
        method: "GET",
        headers: {
            "Content-Type": "application/json",
        },
    });

    if (response.status === 404) {
        // User not found - return null gracefully
        // This can happen when team members are from a different user's provider
        return null;
    }

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to get user");
    }

    const user = await response.json();
    // Add shortId to the user
    return {
        ...user,
        shortId: extractShortId(user.id),
    };
}


