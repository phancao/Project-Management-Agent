"use client";

import { User } from "lucide-react";
import { WorkspaceLoading } from "~/components/ui/workspace-loading";

interface MemberLoadingOverlayProps {
    isContextLoading: boolean;
    isLoadingUsers: boolean;
    isLoadingTasks: boolean;
}

/**
 * Branded loading overlay for Member Profile page.
 * Tracks initialization of Workspace, User Roster, and Task History.
 */
export function MemberLoadingOverlay({
    isContextLoading,
    isLoadingUsers,
    isLoadingTasks
}: MemberLoadingOverlayProps) {
    const isAnyLoading = isContextLoading || isLoadingUsers || isLoadingTasks;

    if (!isAnyLoading) {
        return null;
    }

    return (
        <WorkspaceLoading
            title="Member Profile"
            subtitle="Gathering workload metrics..."
            items={[
                { label: "Workspace Context", isLoading: isContextLoading },
                { label: "Member Profile", isLoading: isLoadingUsers },
                { label: "Work History", isLoading: isLoadingTasks },
            ]}
            icon={<User className="w-6 h-6 text-white" />}
            overlay={true}
        />
    );
}
