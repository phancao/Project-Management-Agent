import { resolvePMServiceURL } from "~/core/api/resolve-pm-service-url";

export interface PMTimeEntry {
    id: string;
    task_id?: string;
    user_id: string;
    hours: number;
    date: string;
    description?: string;
    activity_type?: string;
}

export interface ListTimeEntriesOptions {
    userIds?: string[];
    startDate?: string;  // YYYY-MM-DD
    endDate?: string;    // YYYY-MM-DD
    projectId?: string;
    providerId?: string;
}

export async function listTimeEntries(options?: {
    projectId?: string;
    userIds?: string[];
    taskId?: string;
    startDate?: string;
    endDate?: string;
    providerId?: string;
}) {
    const pageSize = 500;

    const fetchPage = async (page: number) => {
        const params = new URLSearchParams();
        if (options?.startDate) params.append("start_date", options.startDate);
        if (options?.endDate) params.append("end_date", options.endDate);
        if (options?.userIds && options.userIds.length > 0) {
            options.userIds.forEach(id => params.append("user_id", id));
        }
        if (options?.projectId) params.append("project_id", options.projectId);
        if (options?.providerId) params.append("provider_id", options.providerId);

        // Fixed: Use correct param names that match backend (limit/offset, not pageSize/page)
        params.append("limit", pageSize.toString());
        params.append("offset", ((page - 1) * pageSize).toString());

        let url = resolvePMServiceURL("time_entries");
        const queryString = params.toString();
        if (queryString) url = `${url}?${queryString}`;

        const response = await fetch(url, {
            method: "GET",
            headers: { "Content-Type": "application/json" },
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Failed to list time entries");
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
            if (data.items) allItems = allItems.concat(data.items);
        });
    }

    return allItems;
}
