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

export async function listUsers(projectId?: string, providerId?: string): Promise<PMUser[]> {
    console.log('[DEBUG API] listUsers called - projectId:', projectId, 'providerId:', providerId);

    const pageSize = 100;

    const fetchPage = async (page: number) => {
        let url = resolvePMServiceURL("users");
        const params = new URLSearchParams();
        if (projectId) params.append("project_id", projectId);
        if (providerId) params.append("provider_id", providerId);
        params.append("pageSize", pageSize.toString());
        params.append("page", page.toString());

        const response = await fetch(`${url}?${params.toString()}`, {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
            },
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Failed to list users");
        }

        return await response.json();
    };

    // 1. Fetch first page to get metadata
    const firstPageData = await fetchPage(1);

    let allItems: any[] = [];
    let totalItems = 0;

    if (Array.isArray(firstPageData)) {
        allItems = firstPageData;
    } else {
        totalItems = firstPageData.total || 0;
        allItems = firstPageData.items || [];
    }

    // 2. Fetch remaining pages if needed
    if (totalItems > allItems.length) {
        const totalPages = Math.ceil(totalItems / pageSize);
        const pagePromises = [];

        for (let p = 2; p <= totalPages; p++) {
            pagePromises.push(fetchPage(p));
        }

        const results = await Promise.all(pagePromises);
        results.forEach(data => {
            if (data.items) {
                allItems = allItems.concat(data.items);
            }
        });
    }

    // Add shortId to each user
    return allItems.map((user: Omit<PMUser, 'shortId'>) => ({
        ...user,
        shortId: extractShortId(user.id),
    }));
}

/**
 * Fetch a single user by ID.
 * Returns null if user not found (instead of throwing).
 */
export async function getUser(userId: string, providerId?: string): Promise<PMUser | null> {
    console.log('[DEBUG API] getUser called - userId:', userId, 'providerId:', providerId);
    // If providerId is supplied, pass it as query param
    let url = resolvePMServiceURL(`users/${userId}`);
    if (providerId) {
        url += `?provider_id=${providerId}`;
    }

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


