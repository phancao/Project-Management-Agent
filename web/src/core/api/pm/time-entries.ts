import { resolvePMServiceURL } from "~/core/api/resolve-pm-service-url";

export interface PMTimeEntry {
    id: string;
    task_id?: string;
    user_id: string;
    hours: number;
    date: string;
    description?: string;
}

export async function listTimeEntries(userIds?: string[]): Promise<PMTimeEntry[]> {
    const params = new URLSearchParams();

    // API supports user_id filter (singular). 
    // If we have multiple, we might need multiple calls or filter client side.
    // For now, if we have just one, pass it. Else don't pass and filter later?
    // Or just fetch recent.
    if (userIds && userIds.length === 1) {
        params.append("user_id", userIds[0]!);
    }

    let url = resolvePMServiceURL("time_entries");
    const queryString = params.toString();
    if (queryString) {
        url = `${url}?${queryString}`;
    }

    const response = await fetch(url, {
        method: "GET",
        headers: {
            "Content-Type": "application/json",
        },
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to list time entries");
    }

    const data = await response.json();
    return data.items || [];
}
