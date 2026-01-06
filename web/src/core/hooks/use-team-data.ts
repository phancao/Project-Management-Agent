import { useQuery, useQueries } from "@tanstack/react-query";
import { listUsers, type PMUser } from "../api/pm/users";
import { listTasks, type PMTask } from "../api/pm/tasks";
import { listTimeEntries, type PMTimeEntry } from "../api/pm/time-entries";
import { useMemo } from "react";

export function useTeamData(memberIds: string[]) {
    // 1. Fetch All Users (to resolve member details)
    // In a real large app, we might want to fetch only specific IDs, but our API list_users fetches all.
    // Client-side filtering is fine for now (< 1000 users).
    // Cache users for 5 minutes to avoid refetching on every search
    const usersQuery = useQuery({
        queryKey: ['pm', 'users'],
        queryFn: () => listUsers(),
        staleTime: 5 * 60 * 1000, // 5 minutes - don't refetch if data is less than 5 mins old
        gcTime: 10 * 60 * 1000,   // 10 minutes - keep in cache for 10 mins
    });

    const teamMembers = (usersQuery.data || []).filter(u => memberIds.includes(u.id));

    // 2. Fetch Tasks for Team Members - PARALLEL per-member fetching
    // Backend only supports single assignee_id, so we fetch in parallel for each member
    // Use status='open' to only fetch active tasks (excludes closed/done)
    const taskQueries = useQueries({
        queries: memberIds.map(memberId => ({
            queryKey: ['pm', 'tasks', 'member', memberId, 'open'],
            queryFn: () => listTasks({ assignee_ids: [memberId], status: 'open' }),
            staleTime: 2 * 60 * 1000,
            gcTime: 5 * 60 * 1000,
        })),
    });

    // Combine all task results
    const teamTasks = useMemo(() => {
        const taskMap = new Map<string, PMTask>();
        taskQueries.forEach(query => {
            (query.data || []).forEach((task: PMTask) => {
                taskMap.set(task.id, task);
            });
        });
        return Array.from(taskMap.values());
    }, [taskQueries]);

    // IMPORTANT: If memberIds is empty, we're still waiting for member data
    const isLoadingTasks = memberIds.length === 0 || taskQueries.some(q => q.isLoading);

    // 3. Fetch Time Entries (e.g., last 30 days)
    const timeQuery = useQuery({
        queryKey: ['pm', 'time_entries', 'recent'],
        queryFn: () => {
            const startDate = new Date();
            startDate.setDate(startDate.getDate() - 30);
            return listTimeEntries();
        },
        enabled: memberIds.length > 0
    });

    const teamTimeEntries = (timeQuery.data || []).filter(te =>
        memberIds.includes(te.user_id)
    );

    return {
        members: teamMembers,
        tasks: teamTasks,
        timeEntries: teamTimeEntries,
        isLoading: usersQuery.isLoading || isLoadingTasks || timeQuery.isLoading,
        // Granular loading states for transparent progress indicators
        isLoadingUsers: usersQuery.isLoading,
        isLoadingTasks,
        isLoadingTimeEntries: timeQuery.isLoading,
        // Error states
        error: usersQuery.error || taskQueries.find(q => q.error)?.error || timeQuery.error,
        // Expose raw users for "Add Member" search
        allUsers: usersQuery.data || [],
        // Data counts for display
        usersCount: usersQuery.data?.length || 0,
        tasksCount: teamTasks.length,
        timeEntriesCount: timeQuery.data?.length || 0,
    };
}
