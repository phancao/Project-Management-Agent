"use client";

import React from "react";
import { BurndownView } from "../../views/burndown-view";
import { VelocityView } from "../../views/velocity-view";
import { SprintReportView } from "../../views/sprint-report-view";
import { CFDView } from "../../views/cfd-view";
import { CycleTimeView } from "../../views/cycle-time-view";
import { WorkDistributionView } from "../../views/work-distribution-view";
import { IssueTrendView } from "../../views/issue-trend-view";
import { WorklogsView } from "../../views/worklogs-view";

// Wrappers to ensure they match the DashboardPlugin component signature
// and to allow for future configuration injection if needed.

export const BurndownPage = ({ config }: { config: any }) => <BurndownView />;
export const VelocityPage = ({ config }: { config: any }) => <VelocityView />;
export const SprintReportPage = ({ config }: { config: any }) => <SprintReportView />;
export const CFDPage = ({ config }: { config: any }) => <CFDView />;
export const CycleTimePage = ({ config }: { config: any }) => <CycleTimeView />;
export const WorkDistributionPage = ({ config }: { config: any }) => <WorkDistributionView />;
export const IssueTrendPage = ({ config }: { config: any }) => <IssueTrendView />;
export const WorklogsPage = ({ config }: { config: Record<string, any> }) => (
    <WorklogsView
        providerId={config.providerId}
        projectId={config.projectId}
    />
);
