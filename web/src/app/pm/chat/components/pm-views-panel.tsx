import { CheckSquare, FolderKanban, RefreshCw, LayoutGrid, Plus, X, LayoutTemplate, GripVertical } from "lucide-react";
import { useState } from "react";

import { Button } from "~/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "~/components/ui/tabs";
import { cn } from "~/lib/utils";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragOverlay,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  horizontalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

import { BacklogView } from "./views/backlog-view";
import { SprintBoardView } from "./views/sprint-board-view";
import { StorePanelView } from "./views/store-panel-view";
import { CustomDashboardView } from "./views/custom-dashboard-view";
import { MainDashboardView } from "./views/main-dashboard-view"; // [NEW]
import { useDashboardStore } from "~/core/store/use-dashboard-store";
import { useStoreRegistry } from "./dashboards/registry";
import { toast } from "sonner";

type PMView = "dashboard" | "backlog" | "board" | "store" | string;

interface PMViewsPanelProps {
  className?: string;
}

interface SortableTabProps {
  id: string;
  value: string;
  children: React.ReactNode;
  onClose: (e: React.MouseEvent) => void;
}

function SortableTab({ id, value, children, onClose }: SortableTabProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 50 : "auto",
    opacity: isDragging ? 0.3 : 1, // Make ghost more transparent
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <TabsTrigger
        value={value}
        className={cn(
          "group/tab flex items-center gap-2 px-4 py-2 rounded-xl transition-all duration-300 pr-2 cursor-grab active:cursor-grabbing relative pl-2",
          // Base styles
          "data-[state=active]:bg-brand data-[state=active]:text-white dark:data-[state=active]:bg-brand data-[state=active]:shadow-lg data-[state=active]:shadow-brand/40",
          // Dragging styles
          isDragging && "ring-2 ring-brand ring-offset-2 bg-brand/10 dark:bg-brand/20 border-brand border-dashed border",
          // Hover indication for moveable items
          "hover:bg-gray-100 dark:hover:bg-gray-800/50 hover:pl-2"
        )}
      >
        {/* Grip Handle - Reveals on Hover */}
        <div className="w-0 overflow-hidden group-hover/tab:w-4 transition-all duration-300 opacity-0 group-hover/tab:opacity-100 -ml-1">
          <GripVertical className="w-3 h-3 text-gray-400" />
        </div>
        {children}
      </TabsTrigger>
    </div>
  );
}

export function PMViewsPanel({ className }: PMViewsPanelProps) {
  const [activeView, setActiveView] = useState<PMView>("dashboard"); // Default to Dashboard
  const { pages, uninstallInstance, movePage } = useDashboardStore(); // Use pages for tabs
  const { getPlugin } = useStoreRegistry();

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }), // Require slight movement to start drag
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const handleDragEnd = (event: any) => {
    const { active, over } = event;

    if (active.id !== over.id) {
      const oldIndex = pages.findIndex((p) => p.instanceId === active.id);
      const newIndex = pages.findIndex((p) => p.instanceId === over.id);

      if (oldIndex !== -1 && newIndex !== -1) {
        movePage(oldIndex, newIndex);
      }
    }
  };

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
    return ["dashboard", "backlog", "board", "store"].includes(view);
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

              {/* Dynamic Tabs for Installed Pages Only (Not Widgets) */}
              <DndContext
                sensors={sensors}
                collisionDetection={closestCenter}
                onDragEnd={handleDragEnd}
              >
                <SortableContext
                  items={pages.map(p => p.instanceId)}
                  strategy={horizontalListSortingStrategy}
                >
                  {pages.map((instance) => {
                    const plugin = getPlugin(instance.pluginId);
                    // Allow rendering tab even if plugin missing (so user can close it)
                    const title = instance.config.title || plugin?.meta.title || "Unknown Page";
                    const Icon = plugin?.meta.icon || LayoutGrid;

                    return (
                      <SortableTab
                        key={instance.instanceId}
                        id={instance.instanceId}
                        value={instance.instanceId}
                        onClose={(e) => handleCloseTab(e, instance.instanceId, title)}
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
                      </SortableTab>
                    );
                  })}
                </SortableContext>
              </DndContext>

              {/* Store Tab (Always last) */}
              <TabsTrigger
                value="store"
                className="flex items-center gap-2 px-4 py-2 rounded-xl border border-dashed border-gray-300 dark:border-gray-700 bg-transparent hover:bg-gray-50 dark:hover:bg-gray-900 data-[state=active]:bg-gray-100 dark:data-[state=active]:bg-gray-800 data-[state=active]:text-foreground data-[state=active]:shadow-none"
              >
                <Plus className="w-4 h-4" />
                PM Page Store
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
        {activeView === "store" && <StorePanelView />}

        {/* Render Custom Dashboard Instance (Page) if it's not a standard view */}
        {!isStandardView(activeView) && (
          <CustomDashboardView instanceId={activeView} />
        )}
      </div>
    </div>
  );
}


