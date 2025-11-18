// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { CheckSquare, FolderKanban, LineChart, Calendar, Users, RefreshCw } from "lucide-react";
import { useState } from "react";

import { Button } from "~/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "~/components/ui/tabs";
import { cn } from "~/lib/utils";

import { BacklogView } from "./views/backlog-view";
import { ChartsPanelView } from "./views/charts-panel-view";
import { SprintBoardView } from "./views/sprint-board-view";
import { TeamAssignmentsView } from "./views/team-assignments-view";
import { TimelineView } from "./views/timeline-view";

type PMView = "backlog" | "board" | "charts" | "timeline" | "team";

interface PMViewsPanelProps {
  className?: string;
}

export function PMViewsPanel({ className }: PMViewsPanelProps) {
  const [activeView, setActiveView] = useState<PMView>("backlog");

  const handleRefresh = () => {
    // Trigger pm_refresh event to refresh all data
    window.dispatchEvent(new CustomEvent("pm_refresh", { detail: { type: "pm_refresh" } }));
  };

  return (
    <div className={cn("flex flex-col h-full bg-gray-50 dark:bg-gray-900", className)}>
      {/* Navigation Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <div className="flex items-center justify-between px-4 py-2">
          <Tabs value={activeView} onValueChange={(v) => setActiveView(v as PMView)} className="flex-1">
            <TabsList className="w-full justify-start h-auto bg-transparent p-0 gap-1">
            <TabsTrigger 
              value="backlog"
              className="flex items-center gap-2 px-4 py-2 data-[state=active]:bg-blue-50 data-[state=active]:text-blue-600 dark:data-[state=active]:bg-blue-900/20"
            >
              <CheckSquare className="w-4 h-4" />
              Backlog
            </TabsTrigger>
            <TabsTrigger 
              value="board"
              className="flex items-center gap-2 px-4 py-2 data-[state=active]:bg-blue-50 data-[state=active]:text-blue-600 dark:data-[state=active]:bg-blue-900/20"
            >
              <FolderKanban className="w-4 h-4" />
              Board
            </TabsTrigger>
            <TabsTrigger 
              value="charts"
              className="flex items-center gap-2 px-4 py-2 data-[state=active]:bg-blue-50 data-[state=active]:text-blue-600 dark:data-[state=active]:bg-blue-900/20"
            >
              <LineChart className="w-4 h-4" />
              Charts
            </TabsTrigger>
            <TabsTrigger 
              value="timeline"
              className="flex items-center gap-2 px-4 py-2 data-[state=active]:bg-blue-50 data-[state=active]:text-blue-600 dark:data-[state=active]:bg-blue-900/20"
            >
              <Calendar className="w-4 h-4" />
              Timeline
            </TabsTrigger>
            <TabsTrigger 
              value="team"
              className="flex items-center gap-2 px-4 py-2 data-[state=active]:bg-blue-50 data-[state=active]:text-blue-600 dark:data-[state=active]:bg-blue-900/20"
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
            className="gap-2 ml-2 shrink-0"
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
        {activeView === "team" && <TeamAssignmentsView />}
      </div>
    </div>
  );
}

