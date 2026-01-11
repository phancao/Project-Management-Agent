// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "~/components/ui/tabs";
import { BurndownView } from "./burndown-view";
import { VelocityView } from "./velocity-view";
import { SprintReportView } from "./sprint-report-view";
import { CFDView } from "./cfd-view";
import { CycleTimeView } from "./cycle-time-view";
import { WorkDistributionView } from "./work-distribution-view";
import { IssueTrendView } from "./issue-trend-view";
import { WorklogsView } from "./worklogs-view";

export function ChartsPanelView() {
  const [activeTab, setActiveTab] = useState("burndown");

  return (
    <div className="h-full w-full">
      <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
        <TabsList className="w-full justify-start bg-transparent backdrop-blur-sm border-b border-gray-200 dark:border-gray-700 rounded-none p-2">
          <TabsTrigger value="burndown" className="px-4 py-2 rounded-xl transition-all duration-300 data-[state=active]:shadow-lg data-[state=active]:shadow-brand/40 border border-transparent data-[state=active]:border-indigo-500/30 dark:data-[state=active]:border-indigo-500/40">
            📉 Burndown
          </TabsTrigger>
          <TabsTrigger value="velocity" className="px-4 py-2 rounded-xl transition-all duration-300 data-[state=active]:shadow-lg data-[state=active]:shadow-brand/40 border border-transparent data-[state=active]:border-indigo-500/30 dark:data-[state=active]:border-indigo-500/40">
            ⚡ Velocity
          </TabsTrigger>
          <TabsTrigger value="sprint-report" className="px-4 py-2 rounded-xl transition-all duration-300 data-[state=active]:shadow-lg data-[state=active]:shadow-brand/40 border border-transparent data-[state=active]:border-indigo-500/30 dark:data-[state=active]:border-indigo-500/40">
            📊 Sprint Report
          </TabsTrigger>
          <TabsTrigger value="cfd" className="px-4 py-2 rounded-xl transition-all duration-300 data-[state=active]:shadow-lg data-[state=active]:shadow-brand/40 border border-transparent data-[state=active]:border-indigo-500/30 dark:data-[state=active]:border-indigo-500/40">
            📈 CFD
          </TabsTrigger>
          <TabsTrigger value="cycle-time" className="px-4 py-2 rounded-xl transition-all duration-300 data-[state=active]:shadow-lg data-[state=active]:shadow-brand/40 border border-transparent data-[state=active]:border-indigo-500/30 dark:data-[state=active]:border-indigo-500/40">
            ⏱️ Cycle Time
          </TabsTrigger>
          <TabsTrigger value="work-distribution" className="px-4 py-2 rounded-xl transition-all duration-300 data-[state=active]:shadow-lg data-[state=active]:shadow-brand/40 border border-transparent data-[state=active]:border-indigo-500/30 dark:data-[state=active]:border-indigo-500/40">
            🥧 Distribution
          </TabsTrigger>
          <TabsTrigger value="issue-trend" className="px-4 py-2 rounded-xl transition-all duration-300 data-[state=active]:shadow-lg data-[state=active]:shadow-brand/40 border border-transparent data-[state=active]:border-indigo-500/30 dark:data-[state=active]:border-indigo-500/40">
            📊 Trend
          </TabsTrigger>
          <TabsTrigger value="worklogs" className="px-4 py-2 rounded-xl transition-all duration-300 data-[state=active]:shadow-lg data-[state=active]:shadow-brand/40 border border-transparent data-[state=active]:border-indigo-500/30 dark:data-[state=active]:border-indigo-500/40">
            ⏱️ Worklogs
          </TabsTrigger>
        </TabsList>

        <div className="flex-1 overflow-auto">
          <TabsContent value="burndown" className="mt-0 h-full">
            <BurndownView />
          </TabsContent>

          <TabsContent value="velocity" className="mt-0 h-full">
            <VelocityView />
          </TabsContent>

          <TabsContent value="sprint-report" className="mt-0 h-full">
            <SprintReportView />
          </TabsContent>

          <TabsContent value="cfd" className="mt-0 h-full">
            <CFDView />
          </TabsContent>

          <TabsContent value="cycle-time" className="mt-0 h-full">
            <CycleTimeView />
          </TabsContent>

          <TabsContent value="work-distribution" className="mt-0 h-full">
            <WorkDistributionView />
          </TabsContent>

          <TabsContent value="issue-trend" className="mt-0 h-full">
            <IssueTrendView />
          </TabsContent>

          <TabsContent value="worklogs" className="mt-0 h-full">
            <WorklogsView />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}

