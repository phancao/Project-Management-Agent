import { resolvePMServiceURL } from "~/core/api/resolve-pm-service-url";

export interface PMTask {
    id: string;
    name: string;
    status: string;
    assignee_id?: string;
    project_id?: string;
    deadline?: string;
    estimated_hours?: number;
    spent_hours?: number;
    remaining_hours?: number;
    actual_hours?: number;
    title?: string; // Often aliased to name in response
    has_children?: boolean;
}

export async function listTasks(filters: { assignee_ids?: string[], project_id?: string }): Promise<PMTask[]> {
    const params = new URLSearchParams();

    // For now, if we have specific filters supported by API, add them.
    // The list_tasks endpoint supports: project_id, sprint_id, assignee_id, status.
    if (filters.project_id) {
        params.append("project_id", filters.project_id);
    }
    // We handle assignee_ids array by fetching active tasks or passing the first one if we want to be specific
    if (filters.assignee_ids && filters.assignee_ids.length > 0) {
        params.append("assignee_id", filters.assignee_ids[0]!);
    }

    let url = resolvePMServiceURL("tasks");
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
        throw new Error(error.detail || "Failed to list tasks");
    }

    const data = await response.json();
    return data.items || [];
}
