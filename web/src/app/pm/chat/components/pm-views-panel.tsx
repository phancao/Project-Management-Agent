import { CheckSquare, FolderKanban, LineChart, Calendar, Users, RefreshCw, Timer, LayoutGrid, Plus, X, LayoutTemplate } from "lucide-react";
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
import { StorePanelView } from "./views/store-panel-view";
import { CustomDashboardView } from "./views/custom-dashboard-view";
import { MainDashboardView } from "./views/main-dashboard-view"; // [NEW]
import { useDashboardStore } from "~/core/store/use-dashboard-store";
import { getDashboardPlugin } from "./dashboards/registry";
import { toast } from "sonner";

type PMView = "dashboard" | "backlog" | "board" | "charts" | "timeline" | "team" | "efficiency" | "store" | string;

interface PMViewsPanelProps {
  className?: string;
}

export function PMViewsPanel({ className }: PMViewsPanelProps) {
  const [activeView, setActiveView] = useState<PMView>("dashboard"); // Default to Dashboard
  const { pages, uninstallInstance } = useDashboardStore(); // Use pages for tabs

  const handleRefresh = () => {
    // Trigger pm_refresh event to refresh all data
    window.dispatchEvent(new CustomEvent("pm_refresh", { detail: { type: "pm_refresh" } }));
  };

  // Handle view change to support custom dashboards
  const handleViewChange = (view: string) => {
    setActiveView(view);
  };

  const handleCloseTab = (e: React.MouseEvent, instanceId: string, title: string) => {
    e.stopPropagation(); // Prevent tab switch

    // Switch to dashboard if closing active tab
    if (activeView === instanceId) {
      setActiveView("dashboard");
    }

    uninstallInstance(instanceId);
    toast.info(`Closed "${title}" tab`);
  };

  // Helper to check if current view is a standard view
  const isStandardView = (view: string) => {
    return ["dashboard", "backlog", "board", "charts", "timeline", "efficiency", "team", "store"].includes(view);
  };

  return (
    <div className={cn("flex flex-col h-full bg-transparent", className)}>
      {/* Navigation Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700 bg-transparent backdrop-blur-sm">
        <div className="flex items-center justify-between px-4 py-2">
          <Tabs value={activeView} onValueChange={handleViewChange} className="flex-1 overflow-hidden">
            <TabsList className="w-full justify-start h-auto bg-transparent p-0 gap-1 overflow-x-auto no-scrollbar scroll-smooth py-1">

              {/* Main Dashboard Tab - Always First */}
              <TabsTrigger
                value="dashboard"
                className="flex items-center gap-2 px-4 py-2 rounded-xl transition-all duration-300 data-[state=active]:bg-brand data-[state=active]:text-white dark:data-[state=active]:bg-brand data-[state=active]:shadow-lg data-[state=active]:shadow-brand/40"
              >
                <LayoutTemplate className="w-4 h-4" />
                Dashboard
              </TabsTrigger>

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

              {/* Dynamic Tabs for Installed Pages Only (Not Widgets) */}
              {pages.map((instance) => {
                const plugin = getDashboardPlugin(instance.pluginId);
                // Allow rendering tab even if plugin missing (so user can close it)
                const title = instance.config.title || plugin?.meta.title || "Unknown Page";
                const Icon = plugin?.meta.icon || LayoutGrid;

                return (
                  <TabsTrigger
                    key={instance.instanceId}
                    value={instance.instanceId}
                    className="group/tab flex items-center gap-2 px-4 py-2 rounded-xl transition-all duration-300 data-[state=active]:bg-brand data-[state=active]:text-white dark:data-[state=active]:bg-brand data-[state=active]:shadow-lg data-[state=active]:shadow-brand/40 pr-2"
                  >
                    <Icon className="w-4 h-4" />
                    <span className="truncate max-w-[100px]">{title}</span>
                    <div
                      role="button"
                      onClick={(e) => handleCloseTab(e, instance.instanceId, title)}
                      className="ml-1 p-0.5 rounded-full hover:bg-white/20 opacity-0 group-hover/tab:opacity-100 transition-opacity"
                    >
                      <X className="w-3 h-3" />
                    </div>
                  </TabsTrigger>
                );
              })}

              {/* Store Tab (Always last) */}
              <TabsTrigger
                value="store"
                className="flex items-center gap-2 px-4 py-2 rounded-xl border border-dashed border-gray-300 dark:border-gray-700 bg-transparent hover:bg-gray-50 dark:hover:bg-gray-900 data-[state=active]:bg-gray-100 dark:data-[state=active]:bg-gray-800 data-[state=active]:text-foreground data-[state=active]:shadow-none"
              >
                <Plus className="w-4 h-4" />
                Store
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
        {activeView === "dashboard" && (
          <MainDashboardView />
        )}
        {activeView === "backlog" && <BacklogView />}
        {activeView === "board" && <SprintBoardView />}
        {activeView === "charts" && <ChartsPanelView />}
        {activeView === "timeline" && <TimelineView />}
        {activeView === "efficiency" && <EfficiencyPanelView />}
        {activeView === "team" && <TeamAssignmentsView />}
        {activeView === "store" && <StorePanelView />}

        {/* Render Custom Dashboard Instance (Page) if it's not a standard view */}
        {!isStandardView(activeView) && (
          <CustomDashboardView instanceId={activeView} />
        )}
      </div>
    </div>
  );
}


