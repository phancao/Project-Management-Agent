import { resolvePMServiceURL } from "~/core/api/resolve-pm-service-url";

export interface PMUser {
    id: string;
    name: string;
    email: string;
    avatar?: string;
    roles?: string[];
}

export async function listUsers(projectId?: string): Promise<PMUser[]> {
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
    return data.items || [];
}
