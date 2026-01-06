"use client";

import React, { createContext, useContext, useMemo, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { listUsers, type PMUser } from "~/core/api/pm/users";
import { listTasks, type PMTask } from "~/core/api/pm/tasks";
import { listTimeEntries, type PMTimeEntry } from "~/core/api/pm/time-entries";
import { useTeams } from "~/core/hooks/use-teams";
import { useProjects, type Project } from "~/core/api/hooks/pm/use-projects";

/**
 * Centralized Team Data Context
 * 
 * This provider fetches all team-related data ONCE and shares it across
 * all child components, eliminating duplicate API calls that were happening
 * when each component called useTeamData independently.
 */

interface TeamDataContextValue {
    // Raw data from API
    allUsers: PMUser[];
    allTasks: PMTask[];
    allTimeEntries: PMTimeEntry[];
    allProjects: Project[];

    // Teams data
    teams: Array<{ id: string; name: string; memberIds: string[]; description?: string }>;
    allMemberIds: string[];

    // Filtered team members (users who are in teams)
    teamMembers: PMUser[];
    teamTasks: PMTask[];
    teamTimeEntries: PMTimeEntry[];

    // Loading states
    isLoading: boolean;
    isLoadingTeams: boolean;
    isLoadingUsers: boolean;
    isLoadingTasks: boolean;
    isLoadingTimeEntries: boolean;
    isLoadingProjects: boolean;

    // Fetching states (for showing "Loading..." vs "Loaded X items")
    isFetchingUsers: boolean;
    isFetchingTasks: boolean;
    isFetchingTimeEntries: boolean;
    isFetchingProjects: boolean;

    // Counts for display (available during and after loading)
    usersCount: number;
    tasksCount: number;
    timeEntriesCount: number;
    teamsCount: number;
    projectsCount: number;

    // Errors
    error: Error | null;
}

const TeamDataContext = createContext<TeamDataContextValue | null>(null);

interface TeamDataProviderProps {
    children: ReactNode;
}

export function TeamDataProvider({ children }: TeamDataProviderProps) {
    // 1. Fetch Teams first (this determines which users/tasks we need)
    const { teams, isLoading: isLoadingTeams } = useTeams();

    // 2. Deduplicate all member IDs from teams
    const allMemberIds = useMemo(() => {
        return Array.from(new Set(teams.flatMap(t => t.memberIds)));
    }, [teams]);

    // 3. Fetch Projects
    const { projects, loading: isLoadingProjects, error: projectsError } = useProjects();

    // 4. Fetch ALL users ONCE with proper caching
    const usersQuery = useQuery({
        queryKey: ['pm', 'users'],
        queryFn: () => listUsers(),
        staleTime: 5 * 60 * 1000, // 5 minutes
        gcTime: 10 * 60 * 1000,   // 10 minutes
    });

    // 5. Fetch ALL tasks ONCE
    const tasksQuery = useQuery({
        queryKey: ['pm', 'tasks', 'all_active'],
        queryFn: () => listTasks({}),
        staleTime: 2 * 60 * 1000, // 2 minutes
        gcTime: 5 * 60 * 1000,    // 5 minutes
    });

    // 6. Fetch time entries ONCE
    const timeQuery = useQuery({
        queryKey: ['pm', 'time_entries', 'recent'],
        queryFn: () => listTimeEntries(),
        staleTime: 2 * 60 * 1000, // 2 minutes
        gcTime: 5 * 60 * 1000,    // 5 minutes
    });

    // 7. Filter data for team members (client-side)
    const allUsers = usersQuery.data || [];
    const allTasks = tasksQuery.data || [];
    const allTimeEntries = timeQuery.data || [];
    const allProjects = projects || [];

    const teamMembers = useMemo(() =>
        allUsers.filter(u => allMemberIds.includes(u.id)),
        [allUsers, allMemberIds]
    );

    const teamTasks = useMemo(() =>
        allTasks.filter(t => t.assignee_id && allMemberIds.includes(t.assignee_id)),
        [allTasks, allMemberIds]
    );

    const teamTimeEntries = useMemo(() =>
        allTimeEntries.filter(te => allMemberIds.includes(te.user_id)),
        [allTimeEntries, allMemberIds]
    );

    // Build context value
    const value: TeamDataContextValue = useMemo(() => ({
        // Raw data
        allUsers,
        allTasks,
        allTimeEntries,
        allProjects,

        // Teams
        teams,
        allMemberIds,

        // Filtered for teams
        teamMembers,
        teamTasks,
        teamTimeEntries,

        // Loading states (true when no data yet)
        isLoading: isLoadingTeams || usersQuery.isLoading || tasksQuery.isLoading || timeQuery.isLoading || isLoadingProjects,
        isLoadingTeams,
        isLoadingUsers: usersQuery.isLoading,
        isLoadingTasks: tasksQuery.isLoading,
        isLoadingTimeEntries: timeQuery.isLoading,
        isLoadingProjects,

        // Fetching states (true when fetching, even if we have stale data)
        isFetchingUsers: usersQuery.isFetching,
        isFetchingTasks: tasksQuery.isFetching,
        isFetchingTimeEntries: timeQuery.isFetching,
        isFetchingProjects: isLoadingProjects,

        // Counts - available during loading to show progress
        usersCount: allUsers.length,
        tasksCount: allTasks.length,
        timeEntriesCount: allTimeEntries.length,
        teamsCount: teams.length,
        projectsCount: allProjects.length,

        // Error
        error: usersQuery.error || tasksQuery.error || timeQuery.error || projectsError || null,
    }), [
        allUsers, allTasks, allTimeEntries, allProjects,
        teams, allMemberIds,
        teamMembers, teamTasks, teamTimeEntries,
        isLoadingTeams, isLoadingProjects,
        usersQuery.isLoading, tasksQuery.isLoading, timeQuery.isLoading,
        usersQuery.isFetching, tasksQuery.isFetching, timeQuery.isFetching,
        usersQuery.error, tasksQuery.error, timeQuery.error, projectsError,
    ]);

    return (
        <TeamDataContext.Provider value={value}>
            {children}
        </TeamDataContext.Provider>
    );
}

/**
 * Hook to access centralized team data.
 * Must be used within a TeamDataProvider.
 */
export function useTeamDataContext(): TeamDataContextValue {
    const context = useContext(TeamDataContext);
    if (!context) {
        throw new Error("useTeamDataContext must be used within a TeamDataProvider");
    }
    return context;
}

