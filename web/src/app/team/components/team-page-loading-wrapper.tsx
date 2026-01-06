"use client";

import { useMemo } from "react";
import { useTeams } from "~/core/hooks/use-teams";
import { useTeamData } from "~/core/hooks/use-team-data";
import { LoadingProgress } from "./loading-progress";

interface TeamPageLoadingWrapperProps {
    children: React.ReactNode;
}

/**
 * Wrapper component that shows granular loading progress while team data is being fetched.
 * This provides transparency into what data is being loaded and where it might be stuck.
 */
export function TeamPageLoadingWrapper({ children }: TeamPageLoadingWrapperProps) {
    const { teams, isLoading: isLoadingTeams } = useTeams();

    // Deduplicate member IDs from all teams
    const allMemberIds = useMemo(() => {
        return Array.from(new Set(teams.flatMap(t => t.memberIds)));
    }, [teams]);

    const {
        isLoadingUsers,
        isLoadingTasks,
        isLoadingTimeEntries,
        usersCount,
        tasksCount,
        timeEntriesCount,
    } = useTeamData(allMemberIds);

    const isAnyLoading = isLoadingTeams || isLoadingUsers || isLoadingTasks || isLoadingTimeEntries;

    return (
        <>
            {isAnyLoading && (
                <LoadingProgress
                    isLoadingTeams={isLoadingTeams}
                    isLoadingUsers={isLoadingUsers}
                    isLoadingTasks={isLoadingTasks}
                    isLoadingTimeEntries={isLoadingTimeEntries}
                    teamsCount={teams.length}
                    usersCount={usersCount}
                    tasksCount={tasksCount}
                    timeEntriesCount={timeEntriesCount}
                />
            )}
            {children}
        </>
    );
}
