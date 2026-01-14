/**
 * Project-Centric Efficiency Hooks
 * 
 * These hooks fetch data for a specific project, following the Widget Autonomy Standard.
 * They accept projectId and providerId as mandatory parameters.
 */

import { useQuery } from "@tanstack/react-query";
import { resolvePMServiceURL } from "~/core/api/resolve-pm-service-url";
import { listTimeEntries, type PMTimeEntry } from "~/core/api/pm/time-entries";
import { type PMUser } from "~/core/api/pm/users";
import { type PMTask } from "~/core/api/pm/tasks";

// ===========================================
// TYPES
// ===========================================

export interface ProjectEfficiencyOptions {
    startDate?: string;  // YYYY-MM-DD
    endDate?: string;    // YYYY-MM-DD
}

// ===========================================
// Project Members Hook
// ===========================================

async function fetchProjectMembers(projectId: string, providerId: string): Promise<PMUser[]> {
    const params = new URLSearchParams();
    params.append("project_id", projectId);
    params.append("provider_id", providerId);

    const url = `${resolvePMServiceURL("users")}?${params.toString()}`;

    const response = await fetch(url, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: "Failed to fetch project members" }));
        throw new Error(error.detail || "Failed to fetch project members");
    }

    const data = await response.json();
    // Handle both array and paginated response formats
    return Array.isArray(data) ? data : (data.items || []);
}

export function useProjectMembers(projectId: string | undefined, providerId: string | undefined) {
    return useQuery({
        queryKey: ["pm", "project-members", projectId, providerId],
        queryFn: async () => {
            if (!projectId || !providerId) return [];
            return fetchProjectMembers(projectId, providerId);
        },
        enabled: !!projectId && !!providerId,
        staleTime: 5 * 60 * 1000, // 5 minutes
    });
}

// ===========================================
// Project Tasks Hook
// ===========================================

async function fetchProjectTasks(
    projectId: string,
    providerId: string,
    options?: ProjectEfficiencyOptions
): Promise<PMTask[]> {
    const params = new URLSearchParams();
    params.append("project_id", projectId);
    params.append("provider_id", providerId);
    if (options?.startDate) params.append("start_date", options.startDate);
    if (options?.endDate) params.append("end_date", options.endDate);

    const url = `${resolvePMServiceURL("tasks")}?${params.toString()}`;

    const response = await fetch(url, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: "Failed to fetch project tasks" }));
        throw new Error(error.detail || "Failed to fetch project tasks");
    }

    const data = await response.json();
    // Handle both array and paginated response formats
    return Array.isArray(data) ? data : (data.items || []);
}

export function useProjectTasks(
    projectId: string | undefined,
    providerId: string | undefined,
    options?: ProjectEfficiencyOptions
) {
    return useQuery({
        queryKey: ["pm", "project-tasks", projectId, providerId, options?.startDate, options?.endDate],
        queryFn: async () => {
            if (!projectId || !providerId) return [];
            return fetchProjectTasks(projectId, providerId, options);
        },
        enabled: !!projectId && !!providerId,
        staleTime: 5 * 60 * 1000,
    });
}

// ===========================================
// Project Time Entries Hook
// ===========================================

export function useProjectTimeEntries(
    projectId: string | undefined,
    providerId: string | undefined,
    options?: ProjectEfficiencyOptions
) {
    return useQuery({
        queryKey: ["pm", "project-time-entries", projectId, providerId, options?.startDate, options?.endDate],
        queryFn: async () => {
            if (!projectId || !providerId) return [];
            return listTimeEntries({
                projectId,
                providerId,
                startDate: options?.startDate,
                endDate: options?.endDate,
            });
        },
        enabled: !!projectId && !!providerId,
        staleTime: 5 * 60 * 1000,
    });
}
