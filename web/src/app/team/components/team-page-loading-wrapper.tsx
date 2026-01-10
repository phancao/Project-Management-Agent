"use client";

import { useMemo } from "react";
import { useTeams } from "~/core/hooks/use-teams";
import { useTeamData } from "~/core/hooks/use-team-data";
import { WorkspaceLoading } from "~/components/ui/workspace-loading";
import { Users } from "lucide-react";

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

    if (!isAnyLoading) {
        return <>{children}</>;
    }

    return (
        <>
            <WorkspaceLoading
                title="Loading Team Data"
                subtitle="Fetching from providers..."
                items={[
                    { label: "Teams", isLoading: isLoadingTeams, count: teams.length },
                    { label: "Users", isLoading: isLoadingUsers, count: usersCount },
                    { label: "Tasks", isLoading: isLoadingTasks, count: tasksCount },
                    { label: "Time Entries", isLoading: isLoadingTimeEntries, count: timeEntriesCount },
                ]}
                icon={<Users className="w-6 h-6 text-white" />}
                overlay={true}
            />
            {children}
        </>
    );
}
