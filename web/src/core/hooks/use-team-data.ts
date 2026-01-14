import { useQuery, useQueries } from "@tanstack/react-query";
import { getUser, type PMUser } from "../api/pm/users";
import { listTasks, type PMTask } from "../api/pm/tasks";
import { listTimeEntries, type PMTimeEntry } from "../api/pm/time-entries";
import { useMemo } from "react";

export function useTeamData(memberIds: string[]) {

    // 1. Fetch ONLY specific team members by ID (not all 500 users)
    const userQueries = useQueries({
        queries: memberIds.map(memberId => ({
            queryKey: ['pm', 'user', memberId],
            queryFn: () => getUser(memberId),
            staleTime: 5 * 60 * 1000, // 5 minutes
            gcTime: 10 * 60 * 1000,   // 10 minutes
            retry: false, // Don't retry - user might not exist
        })),
    });

    const teamMembers = useMemo(() => {
        return userQueries
            .filter(q => q.data)
            .map(q => q.data as PMUser);
    }, [userQueries]);

    // Empty memberIds is valid (no members), not a loading state
    const isLoadingUsers = memberIds.length > 0 && userQueries.some(q => q.isLoading);

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

    // Empty memberIds is valid (no tasks), not a loading state
    const isLoadingTasks = memberIds.length > 0 && taskQueries.some(q => q.isLoading);

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
        isLoading: isLoadingUsers || isLoadingTasks || timeQuery.isLoading,
        // Granular loading states for transparent progress indicators
        isLoadingUsers,
        isLoadingTasks,
        isLoadingTimeEntries: timeQuery.isLoading,
        // Error states
        error: userQueries.find(q => q.error)?.error || taskQueries.find(q => q.error)?.error || timeQuery.error,
        // Expose team members (not all users - that's deprecated)
        allUsers: teamMembers,
        // Data counts for display
        usersCount: teamMembers.length,
        tasksCount: teamTasks.length,
        timeEntriesCount: timeQuery.data?.length || 0,
    };
}
