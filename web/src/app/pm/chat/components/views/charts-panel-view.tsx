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

export function ChartsPanelView() {
  const [activeTab, setActiveTab] = useState("burndown");

  return (
    <div className="h-full w-full">
      <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
        <TabsList className="w-full justify-start bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 rounded-none p-2">
          <TabsTrigger value="burndown" className="px-4 py-2">
            📉 Burndown
          </TabsTrigger>
          <TabsTrigger value="velocity" className="px-4 py-2">
            ⚡ Velocity
          </TabsTrigger>
          <TabsTrigger value="sprint-report" className="px-4 py-2">
            📊 Sprint Report
          </TabsTrigger>
          <TabsTrigger value="cfd" className="px-4 py-2">
            📈 CFD
          </TabsTrigger>
          <TabsTrigger value="cycle-time" className="px-4 py-2">
            ⏱️ Cycle Time
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
        </div>
      </Tabs>
    </div>
  );
}

