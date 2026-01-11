// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { CheckSquare, FolderKanban, LineChart, Calendar, Users, RefreshCw, Timer } from "lucide-react";
import { useState } from "react";

import { Button } from "~/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "~/components/ui/tabs";
import { cn } from "~/lib/utils";

import { BacklogView } from "./views/backlog-view";
import { ChartsPanelView } from "./views/charts-panel-view";
import { EfficiencyPanelView } from "./views/efficiency-panel-view";
import { SprintBoardView } from "./views/sprint-board-view";
import { TeamAssignmentsView } from "./views/team-assignments-view";
import { TimelineView } from "./views/timeline-view";

type PMView = "backlog" | "board" | "charts" | "timeline" | "team" | "efficiency";

interface PMViewsPanelProps {
  className?: string;
}

export function PMViewsPanel({ className }: PMViewsPanelProps) {
  const [activeView, setActiveView] = useState<PMView>("backlog");

  const handleRefresh = () => {
    // Trigger pm_refresh event to refresh all data
    window.dispatchEvent(new CustomEvent("pm_refresh", { detail: { type: "pm_refresh" } }));
  };

  // Views handle their own loading states - no blocking here

  return (
    <div className={cn("flex flex-col h-full bg-transparent", className)}>
      {/* Navigation Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700 bg-transparent backdrop-blur-sm">
        <div className="flex items-center justify-between px-4 py-2">
          <Tabs value={activeView} onValueChange={(v) => setActiveView(v as PMView)} className="flex-1 overflow-hidden">
            <TabsList className="w-full justify-start h-auto bg-transparent p-0 gap-1 overflow-x-auto no-scrollbar scroll-smooth py-1">
              <TabsTrigger
                value="backlog"
                className="flex items-center gap-2 px-4 py-2 rounded-xl transition-all duration-300 data-[state=active]:bg-brand data-[state=active]:text-white dark:data-[state=active]:bg-brand data-[state=active]:shadow-lg data-[state=active]:shadow-brand/40"
              >
                <CheckSquare className="w-4 h-4" />
                Backlog
              </TabsTrigger>
              <TabsTrigger
                value="board"
                className="flex items-center gap-2 px-4 py-2 rounded-xl transition-all duration-300 data-[state=active]:bg-brand data-[state=active]:text-white dark:data-[state=active]:bg-brand data-[state=active]:shadow-lg data-[state=active]:shadow-brand/40"
              >
                <FolderKanban className="w-4 h-4" />
                Board
              </TabsTrigger>
              <TabsTrigger
                value="charts"
                className="flex items-center gap-2 px-4 py-2 rounded-xl transition-all duration-300 data-[state=active]:bg-brand data-[state=active]:text-white dark:data-[state=active]:bg-brand data-[state=active]:shadow-lg data-[state=active]:shadow-brand/40"
              >
                <LineChart className="w-4 h-4" />
                Charts
              </TabsTrigger>
              <TabsTrigger
                value="timeline"
                className="flex items-center gap-2 px-4 py-2 rounded-xl transition-all duration-300 data-[state=active]:bg-brand data-[state=active]:text-white dark:data-[state=active]:bg-brand data-[state=active]:shadow-lg data-[state=active]:shadow-brand/40"
              >
                <Calendar className="w-4 h-4" />
                Timeline
              </TabsTrigger>
              <TabsTrigger
                value="efficiency"
                className="flex items-center gap-2 px-4 py-2 rounded-xl transition-all duration-300 data-[state=active]:bg-brand data-[state=active]:text-white dark:data-[state=active]:bg-brand data-[state=active]:shadow-lg data-[state=active]:shadow-brand/40"
              >
                <Timer className="w-4 h-4" />
                Efficiency
              </TabsTrigger>
              <TabsTrigger
                value="team"
                className="flex items-center gap-2 px-4 py-2 rounded-xl transition-all duration-300 data-[state=active]:bg-brand data-[state=active]:text-white dark:data-[state=active]:bg-brand data-[state=active]:shadow-lg data-[state=active]:shadow-brand/40"
              >
                <Users className="w-4 h-4" />
                Team
              </TabsTrigger>
            </TabsList>
          </Tabs>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            className="gap-2 ml-2 shrink-0 border-indigo-500/20 dark:border-indigo-500/30 shadow-lg shadow-indigo-500/10 dark:shadow-indigo-500/20 hover:border-indigo-400/40 dark:hover:border-indigo-500/50 hover:shadow-xl hover:shadow-indigo-400/20 dark:hover:shadow-indigo-500/30"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </Button>
        </div>
      </div>

      {/* View Content */}
      <div className="flex-1 overflow-auto p-4">
        {activeView === "backlog" && <BacklogView />}
        {activeView === "board" && <SprintBoardView />}
        {activeView === "charts" && <ChartsPanelView />}
        {activeView === "timeline" && <TimelineView />}
        {activeView === "efficiency" && <EfficiencyPanelView />}
        {activeView === "team" && <TeamAssignmentsView />}
      </div>
    </div>
  );
}


