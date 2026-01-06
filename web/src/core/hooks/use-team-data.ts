import { useQuery } from "@tanstack/react-query";
import { listUsers, type PMUser } from "../api/pm/users";
import { listTasks, type PMTask } from "../api/pm/tasks";
import { listTimeEntries, type PMTimeEntry } from "../api/pm/time-entries";

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

    // 2. Fetch Tasks for Team Members
    // Ideally we filter by assignee_id IN [...], but API might not support bulk.
    // We'll fetch all tasks or loop. For now, let's fetch all active tasks and filter client side.
    // Optimization: If memberIds is empty, don't fetch.
    const tasksQuery = useQuery({
        queryKey: ['pm', 'tasks', 'all_active'], // Cache key shared across teams for now
        queryFn: () => listTasks({ /* limit/status not supported by strict types yet, fix later if needed */ }),
        enabled: memberIds.length > 0
    });

    const teamTasks = (tasksQuery.data || []).filter(t =>
        t.assignee_id && memberIds.includes(t.assignee_id)
    );

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
        isLoading: usersQuery.isLoading || tasksQuery.isLoading || timeQuery.isLoading,
        // Granular loading states for transparent progress indicators
        isLoadingUsers: usersQuery.isLoading,
        isLoadingTasks: tasksQuery.isLoading,
        isLoadingTimeEntries: timeQuery.isLoading,
        // Error states
        error: usersQuery.error || tasksQuery.error || timeQuery.error,
        // Expose raw users for "Add Member" search
        allUsers: usersQuery.data || [],
        // Data counts for display
        usersCount: usersQuery.data?.length || 0,
        tasksCount: tasksQuery.data?.length || 0,
        timeEntriesCount: timeQuery.data?.length || 0,
    };
}
