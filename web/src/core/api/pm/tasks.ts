import { resolvePMServiceURL } from "~/core/api/resolve-pm-service-url";

export interface PMTask {
    id: string;
    name: string;
    status: string;
    assignee_id?: string;
    project_id?: string;
    deadline?: string; // Legacy field?
    due_date?: string; // Correct field from backend headers
    estimated_hours?: number;
    spent_hours?: number;
    remaining_hours?: number;
    actual_hours?: number;
    start_date?: string;
    title?: string; // Often aliased to name in response
    has_children?: boolean;
}

export async function listTasks(filters: {
    assignee_ids?: string[],
    project_id?: string,
    status?: string, // 'open' = only active tasks, 'all' = include closed
    startDate?: string,
    endDate?: string,
    providerId?: string // [NEW] Enforce specific provider
}): Promise<PMTask[]> {

    const pageSize = 100;

    const fetchPage = async (page: number) => {
        const params = new URLSearchParams();

        if (filters.project_id) {
            params.append("project_id", filters.project_id);
        }
        if (filters.providerId) {
            params.append("provider_id", filters.providerId);
        }
        if (filters.assignee_ids && filters.assignee_ids.length > 0) {
            params.append("assignee_id", filters.assignee_ids[0]!);
        }
        if (filters.status) {
            params.append("status", filters.status);
        }
        if (filters.startDate) {
            params.append("start_date", filters.startDate);
        }
        if (filters.endDate) {
            params.append("end_date", filters.endDate);
        }

        params.append("pageSize", pageSize.toString());
        params.append("page", page.toString());

        let url = resolvePMServiceURL("tasks");
        const queryString = params.toString();
        if (queryString) {
            url = `${url}?${queryString}`;
        }

        const response = await fetch(url, {
            method: "GET",
            headers: { "Content-Type": "application/json" },
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Failed to list tasks");
        }

        return await response.json();
    };

    // 1. Fetch first page
    const firstPageData = await fetchPage(1);

    let allItems: any[] = [];
    let totalItems = 0;

    if (Array.isArray(firstPageData)) {
        allItems = firstPageData;
    } else {
        allItems = firstPageData.items || [];
        totalItems = firstPageData.total || 0;
    }

    // 2. Fetch remaining pages
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

    return allItems;
}

