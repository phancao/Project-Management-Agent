
import React, { useState } from 'react';
import { WorklogsView } from '../../views/worklogs-view';
import { TeamEfficiencyView } from '../../views/team-efficiency-view';
import { TeamOverview } from "~/app/team/components/team-overview";
import { TeamDataProvider } from "~/app/team/context/team-data-context";
import { MemberProfileContext } from "~/app/team/context/member-profile-context";
import { MemberProfileDialog } from "~/app/team/components/member-profile-dialog";

export const TeamWorklogsPage = ({ config, instanceId }: { config: Record<string, any>; instanceId?: string }) => {
    // config.teamMembers should be an array of string IDs
    const memberIds = config.teamMembers as string[] | undefined;
    return <WorklogsView configuredMemberIds={memberIds} instanceId={instanceId} />;
};

export const TeamEfficiencyPage = ({ config, instanceId }: { config: Record<string, any>; instanceId?: string }) => {
    // config.teamMembers should be an array of string IDs
    const memberIds = config.teamMembers as string[] | undefined;
    const title = config.title as string | undefined;
    return <TeamEfficiencyView configuredMemberIds={memberIds} instanceId={instanceId} title={title} />;
};

export const TeamOverviewPage = ({ config }: { config: Record<string, any> }) => {
    const [selectedMemberId, setSelectedMemberId] = useState<string | null>(null);
    const [dialogOpen, setDialogOpen] = useState(false);

    const openMemberProfile = (memberId: string) => {
        setSelectedMemberId(memberId);
        setDialogOpen(true);
    };

    return (
        <TeamDataProvider>
            <MemberProfileContext.Provider value={{ openMemberProfile }}>
                <div className="p-6">
                    <TeamOverview
                        configuredMemberIds={config.teamMembers as string[] | undefined}
                        providerId={config.providerId}
                    />
                </div>
                <MemberProfileDialog
                    memberId={selectedMemberId}
                    open={dialogOpen}
                    onOpenChange={setDialogOpen}
                />
            </MemberProfileContext.Provider>
        </TeamDataProvider>
    );
};
