// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { BarChart3, CheckSquare, FolderKanban, LineChart, Calendar, Users } from "lucide-react";
import { useState } from "react";

import { Tabs, TabsList, TabsTrigger } from "~/components/ui/tabs";
import { cn } from "~/lib/utils";

import { BacklogView } from "./views/backlog-view";
import { BurndownView } from "./views/burndown-view";
import { DashboardView } from "./views/dashboard-view";
import { SprintBoardView } from "./views/sprint-board-view";
import { TeamAssignmentsView } from "./views/team-assignments-view";
import { TimelineView } from "./views/timeline-view";

type PMView = "dashboard" | "board" | "backlog" | "burndown" | "timeline" | "team";

interface PMViewsPanelProps {
  className?: string;
}

export function PMViewsPanel({ className }: PMViewsPanelProps) {
  const [activeView, setActiveView] = useState<PMView>("dashboard");

  return (
    <div className={cn("flex flex-col h-full bg-gray-50 dark:bg-gray-900", className)}>
      {/* Navigation Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <Tabs value={activeView} onValueChange={(v) => setActiveView(v as PMView)}>
          <TabsList className="w-full justify-start h-auto bg-transparent p-2 gap-1">
            <TabsTrigger 
              value="dashboard" 
              className="flex items-center gap-2 px-4 py-2 data-[state=active]:bg-blue-50 data-[state=active]:text-blue-600 dark:data-[state=active]:bg-blue-900/20"
            >
              <BarChart3 className="w-4 h-4" />
              Dashboard
            </TabsTrigger>
            <TabsTrigger 
              value="board"
              className="flex items-center gap-2 px-4 py-2 data-[state=active]:bg-blue-50 data-[state=active]:text-blue-600 dark:data-[state=active]:bg-blue-900/20"
            >
              <FolderKanban className="w-4 h-4" />
              Board
            </TabsTrigger>
            <TabsTrigger 
              value="backlog"
              className="flex items-center gap-2 px-4 py-2 data-[state=active]:bg-blue-50 data-[state=active]:text-blue-600 dark:data-[state=active]:bg-blue-900/20"
            >
              <CheckSquare className="w-4 h-4" />
              Backlog
            </TabsTrigger>
            <TabsTrigger 
              value="burndown"
              className="flex items-center gap-2 px-4 py-2 data-[state=active]:bg-blue-50 data-[state=active]:text-blue-600 dark:data-[state=active]:bg-blue-900/20"
            >
              <LineChart className="w-4 h-4" />
              Burndown
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
      </div>

      {/* View Content */}
      <div className="flex-1 overflow-auto p-4">
        {activeView === "dashboard" && <DashboardView />}
        {activeView === "board" && <SprintBoardView />}
        {activeView === "backlog" && <BacklogView />}
        {activeView === "burndown" && <BurndownView />}
        {activeView === "timeline" && <TimelineView />}
        {activeView === "team" && <TeamAssignmentsView />}
      </div>
    </div>
  );
}

