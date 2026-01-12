import { CheckSquare, FolderKanban, RefreshCw, LayoutGrid, Plus, X, LayoutTemplate, GripVertical, ShoppingBag } from "lucide-react";
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
  onClose: (e: React.MouseEvent) => void;
  children: React.ReactNode; // Keep children for flexibility, but structure it
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
    opacity: isDragging ? 0.3 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <TabsTrigger
        value={value}
        className={cn(
          "group/tab relative flex items-center justify-center gap-2 px-4 py-2 rounded-xl transition-all duration-300 cursor-grab active:cursor-grabbing",
          "hover:pl-8 hover:pr-8", // Make room for controls on hover

          // Base styles
          "data-[state=active]:bg-brand data-[state=active]:text-white dark:data-[state=active]:bg-brand data-[state=active]:shadow-lg data-[state=active]:shadow-brand/40",

          // Dragging styles
          isDragging && "ring-2 ring-brand ring-offset-2 bg-brand/10 dark:bg-brand/20 border-brand border-dashed border",

          // Hover background (if desired, consistency check?)
          // Standard tabs don't usually have a gray bg, but it helps distinguish the 'card' nature of these dynamic tabs
          "hover:bg-gray-100 dark:hover:bg-gray-800/50"
        )}
      >
        {/* Grip Handle - Absolute Left */}
        <div className="absolute left-2 top-1/2 -translate-y-1/2 opacity-0 group-hover/tab:opacity-100 transition-opacity duration-200">
          <GripVertical className="w-3 h-3 text-gray-400" />
        </div>

        {/* Content (Icon + Text) */}
        {children}

        {/* Close Button - Absolute Right */}
        <div
          role="button"
          onClick={onClose}
          className="absolute right-1 top-1/2 -translate-y-1/2 opacity-0 group-hover/tab:opacity-100 transition-opacity duration-200 p-1 rounded-full hover:bg-black/10 dark:hover:bg-white/20"
        >
          <X className="w-3 h-3" />
        </div>
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
            <TabsList className="justify-start h-auto bg-transparent p-0 gap-1 overflow-x-auto no-scrollbar scroll-smooth py-1">

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
                    // Prioritize live metadata shortTitle for tabs, then title
                    const title = plugin?.meta.shortTitle || plugin?.meta.title || instance.config.title || "Unknown Page";
                    const Icon = plugin?.meta.icon || LayoutGrid;

                    return (
                      <SortableTab
                        key={instance.instanceId}
                        id={instance.instanceId}
                        value={instance.instanceId}
                        onClose={(e) => handleCloseTab(e, instance.instanceId, title)}
                      >
                        <Icon className="w-4 h-4 shrink-0" />
                        <span className="truncate max-w-[200px]">{title}</span>
                      </SortableTab>
                    );
                  })}
                </SortableContext>
              </DndContext>

            </TabsList>
          </Tabs>

          <div className="flex items-center gap-2 ml-2 shrink-0">
            {/* Store Button (Fixed on Right) */}
            <button
              onClick={() => setActiveView("store")}
              className={cn(
                "flex items-center gap-1.5 px-2 py-1 rounded-xl border border-dashed border-gray-300 dark:border-gray-700 bg-transparent hover:bg-gray-50 dark:hover:bg-gray-900 transition-all duration-200",
                activeView === "store" ? "bg-gray-100 dark:bg-gray-800 text-foreground shadow-none" : "text-muted-foreground"
              )}
            >
              <ShoppingBag className="w-4 h-4" />
              <Plus className="w-3 h-3" />
            </button>

            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              title="Refresh Data"
              className="w-8 h-8 p-0 shrink-0 rounded-xl border-indigo-500/20 dark:border-indigo-500/30 shadow-lg shadow-indigo-500/10 dark:shadow-indigo-500/20 hover:border-indigo-400/40 dark:hover:border-indigo-500/50 hover:shadow-xl hover:shadow-indigo-400/20 dark:hover:shadow-indigo-500/30"
            >
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
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


