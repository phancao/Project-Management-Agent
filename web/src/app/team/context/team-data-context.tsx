"use client";

import React, { createContext, useContext, useMemo, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { listUsers, type PMUser } from "~/core/api/pm/users";
import { listTasks, type PMTask } from "~/core/api/pm/tasks";
import { listTimeEntries, type PMTimeEntry } from "~/core/api/pm/time-entries";
import { useTeams } from "~/core/hooks/use-teams";
import { useProjects, type Project } from "~/core/api/hooks/pm/use-projects";

/**
 * Lightweight Team Data Context
 * 
 * This provider only fetches essential data (teams, projects) to minimize initial load time.
 * Heavy data (users, tasks, time entries) is loaded by individual tabs as needed.
 */

interface TeamDataContextValue {
    // Essential data (loaded at startup)
    teams: Array<{ id: string; name: string; memberIds: string[]; description?: string }>;
    allMemberIds: string[];
    allProjects: Project[];

    // Loading states for essential data
    isLoading: boolean;
    isLoadingTeams: boolean;
    isLoadingProjects: boolean;

    // Counts
    teamsCount: number;
    projectsCount: number;

    // Error
    error: Error | null;
}

const TeamDataContext = createContext<TeamDataContextValue | null>(null);

interface TeamDataProviderProps {
    children: ReactNode;
}

export function TeamDataProvider({ children }: TeamDataProviderProps) {
    // 1. Fetch Teams (essential - quick load)
    const { teams, isLoading: isLoadingTeams } = useTeams();

    // 2. Deduplicate all member IDs from teams
    const allMemberIds = useMemo(() => {
        return Array.from(new Set(teams.flatMap(t => t.memberIds)));
    }, [teams]);

    // 3. Fetch Projects (essential - quick load)
    const { projects, loading: isLoadingProjects, error: projectsError } = useProjects();

    const allProjects = projects || [];

    // Build context value - only essential data
    const value: TeamDataContextValue = useMemo(() => ({
        teams,
        allMemberIds,
        allProjects,

        isLoading: isLoadingTeams || isLoadingProjects,
        isLoadingTeams,
        isLoadingProjects,

        teamsCount: teams.length,
        projectsCount: allProjects.length,

        error: projectsError || null,
    }), [
        teams, allMemberIds, allProjects,
        isLoadingTeams, isLoadingProjects,
        projectsError,
    ]);

    return (
        <TeamDataContext.Provider value={value}>
            {children}
        </TeamDataContext.Provider>
    );
}

/**
 * Hook to access centralized team data (essential data only).
 * Must be used within a TeamDataProvider.
 */
export function useTeamDataContext(): TeamDataContextValue {
    const context = useContext(TeamDataContext);
    if (!context) {
        throw new Error("useTeamDataContext must be used within a TeamDataProvider");
    }
    return context;
}

/**
 * Hook for tabs that need users data.
 * Call this within components that need users.
 */
export function useTeamUsers(memberIds: string[]) {
    const usersQuery = useQuery({
        queryKey: ['pm', 'users'],
        queryFn: () => listUsers(),
        staleTime: 5 * 60 * 1000, // 5 minutes
        gcTime: 10 * 60 * 1000,   // 10 minutes
    });

    const allUsers = usersQuery.data || [];
    const teamMembers = useMemo(() =>
        allUsers.filter(u => memberIds.includes(u.id)),
        [allUsers, memberIds]
    );

    return {
        allUsers,
        teamMembers,
        isLoading: usersQuery.isLoading,
        isFetching: usersQuery.isFetching,
        error: usersQuery.error,
        count: allUsers.length,
    };
}

/**
 * Hook for tabs that need tasks data.
 * Call this within components that need tasks.
 */
export function useTeamTasks(memberIds: string[]) {
    const tasksQuery = useQuery({
        queryKey: ['pm', 'tasks', 'all_active'],
        queryFn: () => listTasks({}),
        staleTime: 2 * 60 * 1000, // 2 minutes
        gcTime: 5 * 60 * 1000,    // 5 minutes
    });

    const allTasks = tasksQuery.data || [];
    const teamTasks = useMemo(() =>
        allTasks.filter(t => t.assignee_id && memberIds.includes(t.assignee_id)),
        [allTasks, memberIds]
    );

    return {
        allTasks,
        teamTasks,
        isLoading: tasksQuery.isLoading,
        isFetching: tasksQuery.isFetching,
        error: tasksQuery.error,
        count: allTasks.length,
    };
}

/**
 * Hook for tabs that need time entries data.
 * Call this within components that need time entries.
 */
export function useTeamTimeEntries(memberIds: string[]) {
    const timeQuery = useQuery({
        queryKey: ['pm', 'time_entries', 'recent'],
        queryFn: () => listTimeEntries(),
        staleTime: 2 * 60 * 1000, // 2 minutes
        gcTime: 5 * 60 * 1000,    // 5 minutes
    });

    const allTimeEntries = timeQuery.data || [];
    const teamTimeEntries = useMemo(() =>
        allTimeEntries.filter(te => memberIds.includes(te.user_id)),
        [allTimeEntries, memberIds]
    );

    return {
        allTimeEntries,
        teamTimeEntries,
        isLoading: timeQuery.isLoading,
        isFetching: timeQuery.isFetching,
        error: timeQuery.error,
        count: allTimeEntries.length,
    };
}
