"use client";

import React, { createContext, useContext, useMemo, type ReactNode } from "react";
import { useQuery, useQueries, type UseQueryResult } from "@tanstack/react-query";
import { listUsers, getUser, type PMUser } from "~/core/api/pm/users";
import { listTasks, type PMTask } from "~/core/api/pm/tasks";
import { listTimeEntries, type PMTimeEntry } from "~/core/api/pm/time-entries";
import { useTeams } from "~/core/hooks/use-teams";
import { useProjects, type Project } from "~/core/api/hooks/pm/use-projects";
import { useProviders } from "~/core/api/hooks/pm/use-providers";

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
    // Active provider IDs for filtering
    activeProviderIds: string[];

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

    // 2. Get active providers for memberIds validation
    const { providers, loading: isLoadingProviders } = useProviders();

    // Extract active provider IDs for filtering
    const activeProviderIds = useMemo(() => {
        return providers.map(p => p.id);
    }, [providers]);

    // 3. Deduplicate all member IDs from teams AND filter by active providers
    const allMemberIds = useMemo(() => {
        const rawIds = Array.from(new Set(teams.flatMap(t => t.memberIds)));

        // Filter memberIds to only include those from active providers
        // MemberIds format: "provider_id:user_id"
        const validIds = rawIds.filter(id => {
            const providerId = id.split(':')[0] || '';
            const isValid = activeProviderIds.includes(providerId);
            return isValid || activeProviderIds.length === 0; // Allow all if no providers loaded yet
        });

        return validIds;
    }, [teams, activeProviderIds]);

    // 4. Fetch Projects (essential - quick load)
    const { projects, loading: isLoadingProjects, error: projectsError } = useProjects();

    const allProjects = projects || [];

    // Build context value - only essential data
    const value: TeamDataContextValue = useMemo(() => ({
        teams,
        allMemberIds,
        allProjects,
        activeProviderIds,

        isLoading: isLoadingTeams || isLoadingProjects || isLoadingProviders,
        isLoadingTeams,
        isLoadingProjects,

        teamsCount: teams.length,
        projectsCount: allProjects.length,

        error: projectsError || null,
    }), [
        teams, allMemberIds, allProjects, activeProviderIds,
        isLoadingTeams, isLoadingProjects, isLoadingProviders,
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
 * Fetches ONLY the specific team members by ID (not all 500 users).
 */
export function useTeamUsers(memberIds: string[]) {
    // Safety Net: Filter out members from disabled providers
    const { mappings } = useProviders();

    const activeMemberIds = useMemo(() => {
        if (mappings.isActiveMap.size === 0) return memberIds;

        return memberIds.filter(id => {
            const providerId = id.split(':')[0];
            if (!providerId || id.indexOf(':') === -1) return true;
            return mappings.isActiveMap.get(providerId) !== false;
        });
    }, [memberIds, mappings]);

    // Fetch each team member in parallel by their ID
    const userQueries = useQueries({
        queries: activeMemberIds.map(memberId => ({
            queryKey: ['pm', 'user', memberId],
            queryFn: () => {
                const providerId = memberId.indexOf(':') !== -1 ? memberId.split(':')[0] : undefined;
                return getUser(memberId, providerId);
            },
            enabled: !!memberId && activeMemberIds.includes(memberId), // Only fetch if member is valid and provider is active
            staleTime: 5 * 60 * 1000, // 5 minutes
            gcTime: 10 * 60 * 1000,   // 10 minutes
            retry: false, // Don't retry - user might not exist for this provider
        })),
    });

    // Combine all results into teamMembers array
    const teamMembers = useMemo(() => {
        return userQueries
            .filter(q => q.data)
            .map(q => q.data as PMUser);
    }, [userQueries]);

    // Empty memberIds is a valid state (no members), not a loading state
    // Only loading if we have queries that are actively loading
    const isLoading = activeMemberIds.length > 0 && userQueries.some(q => q.isLoading);
    const isFetching = userQueries.some(q => q.isFetching);
    const error = userQueries.find(q => q.error)?.error || null;

    return {
        allUsers: teamMembers, // Now just returns team members, not all 500 users
        teamMembers,
        isLoading,
        isFetching,
        error,
        count: teamMembers.length,
    };
}

/**
 * Hook for tabs that need tasks data.
 * Groups members by provider, filters disabled providers, queries per-provider.
 */
export function useTeamTasks(memberIds: string[], options?: { startDate?: string; endDate?: string; status?: string }) {
    // Get provider mappings to check active status
    const { mappings, loading: isLoadingProviders } = useProviders();

    // Group members by provider and filter out disabled providers
    const providerGroups = useMemo(() => {
        const groups = new Map<string, string[]>();

        for (const id of memberIds) {
            const providerId = id.split(':')[0];
            if (!providerId || id.indexOf(':') === -1) continue;

            // Skip disabled providers
            if (mappings.isActiveMap.size > 0 && mappings.isActiveMap.get(providerId) === false) {
                continue;
            }

            const existing = groups.get(providerId) || [];
            groups.set(providerId, [...existing, id]);
        }

        return groups;
    }, [memberIds, mappings]);

    // Convert to array for useQueries
    const providerEntries = useMemo(() => Array.from(providerGroups.entries()), [providerGroups]);

    const statusFilter = options?.status || 'open';
    const startDate = options?.startDate || 'all';
    const endDate = options?.endDate || 'all';

    // One query per provider (not per member)
    const taskQueries = useQueries({
        queries: providerEntries.map(([providerId, providerMemberIds]) => ({
            queryKey: ['pm', 'tasks', 'provider', providerId, providerMemberIds.sort().join(','), statusFilter, startDate, endDate],
            queryFn: () => {
                return listTasks({
                    assignee_ids: providerMemberIds,
                    status: statusFilter,
                    startDate: options?.startDate,
                    endDate: options?.endDate,
                    providerId: providerId
                });
            },
            retry: false,
            staleTime: 2 * 60 * 1000,
            gcTime: 5 * 60 * 1000,
            // Only enable after providers are loaded
            enabled: !isLoadingProviders && providerMemberIds.length > 0,
        })),
    });

    // Combine all results, deduplicate by task ID
    const allTasks = useMemo(() => {
        const taskMap = new Map<string, PMTask>();
        taskQueries.forEach(query => {
            (query.data || []).forEach(task => {
                taskMap.set(task.id, task);
            });
        });
        return Array.from(taskMap.values());
    }, [taskQueries]);

    const teamTasks = allTasks;

    // Only loading if providers are loading OR we have active queries loading
    const isLoading = isLoadingProviders || (providerEntries.length > 0 && taskQueries.some(q => q.isLoading));
    const isFetching = taskQueries.some(q => q.isFetching);
    const error = taskQueries.find(q => q.error)?.error || null;

    return {
        allTasks,
        teamTasks,
        isLoading,
        isFetching,
        error,
        count: allTasks.length,
    };
}

/**
 * Hook for tabs that need time entries data.
 * Groups members by provider, queries per-provider, merges results.
 */
export function useTeamTimeEntries(memberIds: string[], options?: { startDate?: string; endDate?: string }) {
    // Get provider mappings to check active status
    const { mappings, loading: isLoadingProviders } = useProviders();

    // Group members by provider and filter out disabled providers
    const providerGroups = useMemo(() => {
        const groups = new Map<string, string[]>();

        for (const id of memberIds) {
            const providerId = id.split(':')[0];
            if (!providerId || id.indexOf(':') === -1) continue;

            // Skip disabled providers
            if (mappings.isActiveMap.size > 0 && mappings.isActiveMap.get(providerId) === false) {
                continue;
            }

            const existing = groups.get(providerId) || [];
            groups.set(providerId, [...existing, id]);
        }

        return groups;
    }, [memberIds, mappings]);

    // Convert to array for useQueries
    const providerEntries = useMemo(() => Array.from(providerGroups.entries()), [providerGroups]);

    const startDate = options?.startDate || 'all';
    const endDate = options?.endDate || 'all';

    // One query per provider
    const timeQueries = useQueries({
        queries: providerEntries.map(([providerId, providerMemberIds]) => ({
            queryKey: ['pm', 'time_entries', 'provider', providerId, providerMemberIds.sort().join(','), startDate, endDate],
            queryFn: async () => {
                return listTimeEntries({
                    userIds: providerMemberIds,
                    startDate: options?.startDate,
                    endDate: options?.endDate,
                    providerId: providerId
                });
            },
            retry: false,
            staleTime: 5 * 60 * 1000,
            gcTime: 10 * 60 * 1000,
            enabled: !isLoadingProviders && providerMemberIds.length > 0,
        })),
    });

    // Merge all time entries from all providers
    const allTimeEntries = useMemo(() => {
        const entries: PMTimeEntry[] = [];
        timeQueries.forEach(query => {
            (query.data || []).forEach(entry => {
                entries.push(entry);
            });
        });
        return entries;
    }, [timeQueries]);

    const teamTimeEntries = useMemo(() => {
        return allTimeEntries.filter(te => memberIds.includes(te.user_id));
    }, [allTimeEntries, memberIds]);

    // Only loading if providers are loading OR we have active queries loading
    const isLoading = isLoadingProviders || (providerEntries.length > 0 && timeQueries.some(q => q.isLoading));
    const isFetching = timeQueries.some(q => q.isFetching);
    const error = timeQueries.find(q => q.error)?.error || null;

    return {
        allTimeEntries,
        teamTimeEntries,
        isLoading,
        isFetching,
        error,
        count: allTimeEntries.length,
    };
}

/**
 * Hook for components that need ALL users (e.g., Add Member dropdown).
 * This is a lazy-loaded hook - set enabled=true only when the dropdown is opened.
 * This avoids loading 500+ users upfront when not needed.
 */
export function useAllUsers(enabled: boolean = false) {
    const usersQuery = useQuery({
        queryKey: ['pm', 'users', 'all'],
        queryFn: () => listUsers(),
        staleTime: 5 * 60 * 1000, // 5 minutes
        gcTime: 10 * 60 * 1000,   // 10 minutes
        enabled, // Only fetch when explicitly enabled
    });

    return {
        allUsers: usersQuery.data || [],
        isLoading: usersQuery.isLoading,
        isFetching: usersQuery.isFetching,
        error: usersQuery.error,
        count: (usersQuery.data || []).length,
    };
}
