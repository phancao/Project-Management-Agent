"use client";

import { useTeamDataContext } from "../context/team-data-context";
import { LoadingProgress } from "./loading-progress";

/**
 * Simple overlay component that uses the centralized TeamDataContext
 * for loading state. This eliminates the duplicate data fetching
 * that was happening in the old TeamPageLoadingWrapper.
 */
export function TeamPageLoadingOverlay() {
    const {
        isLoadingTeams,
        isLoadingUsers,
        isLoadingTasks,
        isLoadingTimeEntries,
        isLoadingProjects,
        teamsCount,
        usersCount,
        tasksCount,
        timeEntriesCount,
        projectsCount,
    } = useTeamDataContext();

    const isAnyLoading = isLoadingTeams || isLoadingUsers || isLoadingTasks || isLoadingTimeEntries || isLoadingProjects;

    if (!isAnyLoading) {
        return null;
    }

    return (
        <LoadingProgress
            isLoadingTeams={isLoadingTeams}
            isLoadingProjects={isLoadingProjects}
            isLoadingUsers={isLoadingUsers}
            isLoadingTasks={isLoadingTasks}
            isLoadingTimeEntries={isLoadingTimeEntries}
            teamsCount={teamsCount}
            projectsCount={projectsCount}
            usersCount={usersCount}
            tasksCount={tasksCount}
            timeEntriesCount={timeEntriesCount}
        />
    );
}

