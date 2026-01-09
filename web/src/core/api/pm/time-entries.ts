import { resolvePMServiceURL } from "~/core/api/resolve-pm-service-url";

export interface PMTimeEntry {
    id: string;
    task_id?: string;
    user_id: string;
    hours: number;
    date: string;
    description?: string;
}

export interface ListTimeEntriesOptions {
    userIds?: string[];
    startDate?: string;  // YYYY-MM-DD
    endDate?: string;    // YYYY-MM-DD
    projectId?: string;
}

export async function listTimeEntries(options?: ListTimeEntriesOptions): Promise<PMTimeEntry[]> {
    const params = new URLSearchParams();

    // Use server-side date filtering for efficient queries
    // This is the proper solution for large datasets
    if (options?.startDate) {
        params.append("start_date", options.startDate);
    }
    if (options?.endDate) {
        params.append("end_date", options.endDate);
    }

    // API supports user_id filter (singular)
    if (options?.userIds && options.userIds.length === 1) {
        params.append("user_id", options.userIds[0]!);
    }

    // Project filter
    if (options?.projectId) {
        params.append("project_id", options.projectId);
    }

    // Request enough entries for filtered date range
    params.append("limit", "5000");

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
