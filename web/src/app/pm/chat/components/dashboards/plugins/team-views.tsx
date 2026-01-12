
import React from 'react';
import { WorklogsView } from '../../views/worklogs-view';
import { EfficiencyPanelView } from '../../views/efficiency-panel-view';

export const TeamWorklogsPage = ({ config }: { config: Record<string, any> }) => {
    // config.teamMembers should be an array of string IDs
    const memberIds = config.teamMembers as string[] | undefined;
    return <WorklogsView configuredMemberIds={memberIds} />;
};

export const TeamEfficiencyPage = ({ config }: { config: Record<string, any> }) => {
    // config.teamMembers should be an array of string IDs
    const memberIds = config.teamMembers as string[] | undefined;
    return <EfficiencyPanelView configuredMemberIds={memberIds} />;
};
