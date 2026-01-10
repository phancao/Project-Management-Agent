"use client";

import { useTeamDataContext } from "../context/team-data-context";
import { Users, Briefcase } from "lucide-react";
import { WorkspaceLoading } from "~/components/ui/workspace-loading";

/**
 * Beautiful loading overlay for Team page initialization.
 * Only shows loading for essential data (Teams, Projects).
 * Heavy data (users, tasks, time entries) loads in individual tabs.
 */
export function TeamPageLoadingOverlay() {
    const {
        isLoadingTeams,
        isLoadingProjects,
        teamsCount,
        projectsCount,
    } = useTeamDataContext();

    const isAnyLoading = isLoadingTeams || isLoadingProjects;

    if (!isAnyLoading) {
        return null;
    }

    return (
        <WorkspaceLoading
            title="Team Management"
            subtitle="Initializing workspace..."
            items={[
                { label: "Teams", isLoading: isLoadingTeams, count: teamsCount },
                { label: "Projects", isLoading: isLoadingProjects, count: projectsCount },
            ]}
            icon={<Users className="w-6 h-6 text-white" />}
            overlay={true}
        />
    );
}
