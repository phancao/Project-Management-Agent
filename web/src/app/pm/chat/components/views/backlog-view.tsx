// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import type { DragEndEvent, DragOverEvent, DragStartEvent, DraggableAttributes } from "@dnd-kit/core";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  closestCorners,
  useDroppable,
  useSensor,
  useSensors
} from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { ChevronDown, ChevronRight, Filter, GripVertical, Search, Plus, Calendar, Loader2 } from "lucide-react";
import { useMemo, useState, useEffect, useCallback, useRef } from "react";
import type { ReactNode } from "react";
import { toast } from "sonner";
import type { SyntheticListenerMap } from "@dnd-kit/core/dist/hooks/utilities";

// @ts-expect-error - Direct import for tree-shaking
import ListTodo from "lucide-react/dist/esm/icons/list-todo";
// @ts-expect-error - Direct import for tree-shaking
import Target from "lucide-react/dist/esm/icons/target";

import { Button } from "~/components/ui/button";
import { cn } from "~/lib/utils";
import { Card } from "~/components/ui/card";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "~/components/ui/dialog";
import { Input } from "~/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";
import { Textarea } from "~/components/ui/textarea";
import { resolveServiceURL } from "~/core/api/resolve-service-url";
import { usePMLoading } from "../../../context/pm-loading-context";
import { useSprints, type Sprint as SprintSummary } from "~/core/api/hooks/pm/use-sprints";
import { useTasks } from "~/core/api/hooks/pm/use-tasks";
import type { Task } from "~/app/pm/types";
import { useEpics, type Epic } from "~/core/api/hooks/pm/use-epics";
import { useStatuses } from "~/core/api/hooks/pm/use-statuses";
import { usePriorities } from "~/core/api/hooks/pm/use-priorities";
import { useProjectData } from "../../../hooks/use-project-data";
import { useTaskFiltering } from "../../../hooks/use-task-filtering";
import { debug } from "../../../utils/debug";

import { TaskDetailsModal } from "../task-details-modal";
import { CreateEpicDialog } from "../create-epic-dialog";

/* ============================================================================
 * TYPES
 * ========================================================================= */

type DragType = 'task' | 'sprint' | 'epic' | null;

interface DragState {
  type: DragType;
  id: string | null;
  sourceSprintId?: string | null;
  overTaskId?: string | null;
}

type SortableSprintSectionProps = Omit<SprintSectionProps, "dragHandleProps" | "isSorting">;

function SortableSprintSection(props: SortableSprintSectionProps) {
  const { sprint } = props;
  const { attributes, listeners, setNodeRef, transform, transition, isDragging, over } = useSortable({
    id: `sprint-${sprint.id}`,
    data: { type: 'sprint', sprintId: sprint.id },
  });

  useEffect(() => {
    // Removed debug logging
    return () => {
      // Removed debug logging
    };
  }, [sprint.id, sprint.status]);

  const style = {
    zIndex: isDragging ? 50 : undefined,
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.85 : undefined,
    position: isDragging ? ("relative" as const) : undefined,
    pointerEvents: isDragging ? ("none" as const) : undefined,
  };

  useEffect(() => {
    if (isDragging) {
      // Removed debug logging
    }
  }, [isDragging, sprint.id]);

  useEffect(() => {
    // Removed debug logging
  }, [over?.id, sprint.id]);

  return (
    <div ref={setNodeRef} style={style}>
      <SprintSection
        {...props}
        dragHandleProps={{ attributes, listeners }}
        isSorting={isDragging}
      />
    </div>
  );
}

interface SprintCategoryDropZoneProps {
  category: SprintStatusCategory;
  title: string;
  descriptionWhenIdle: string;
  descriptionWhenDragging: string;
  isSprintDragging: boolean;
}

function SprintCategoryDropZone({
  category,
  title,
  descriptionWhenIdle,
  descriptionWhenDragging,
  isSprintDragging,
}: SprintCategoryDropZoneProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: `sprint-category-${category}`,
  });

  return (
    <div
      ref={setNodeRef}
      className={[
        "rounded-lg border-2 border-dashed px-4 py-8 text-center transition-colors duration-150",
        isOver
          ? "border-blue-400 bg-blue-50 text-blue-600 dark:border-blue-500 dark:bg-blue-900/20 dark:text-blue-200"
          : "border-gray-300 bg-gray-50 text-gray-500 dark:border-gray-600 dark:bg-gray-800/40 dark:text-gray-400",
      ].join(" ")}
    >
      <div className="text-sm font-medium text-gray-600 dark:text-gray-300">{title}</div>
      <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
        {isSprintDragging ? descriptionWhenDragging : descriptionWhenIdle}
      </div>
    </div>
  );
}

function SprintDropPlaceholder() {
  return (
    <div className="mb-4">
      <div className="h-12 rounded-lg border-2 border-dashed border-blue-400 bg-blue-50 dark:border-blue-500 dark:bg-blue-900/20 flex items-center justify-center text-xs font-medium text-blue-600 dark:text-blue-200">
        Drop sprint here
      </div>
    </div>
  );
}

type SprintStatusCategory = "active" | "future" | "closed" | "other";

const ACTIVE_STATUS_VALUES = new Set(["active", "in_progress", "ongoing"]);
const FUTURE_STATUS_VALUES = new Set(["future", "planned", "planning"]);
const CLOSED_STATUS_VALUES = new Set(["closed", "completed"]);

const ORDERED_STATUS_CATEGORIES: SprintStatusCategory[] = ["active", "future", "closed", "other"];

function getSprintStatusCategory(status?: string): SprintStatusCategory {
  const normalized = (status ?? "").toLowerCase();
  if (ACTIVE_STATUS_VALUES.has(normalized)) return "active";
  if (FUTURE_STATUS_VALUES.has(normalized)) return "future";
  if (CLOSED_STATUS_VALUES.has(normalized)) return "closed";
  return "other";
}

function getSprintTimestamp(sprint: SprintSummary): number {
  const start = sprint.start_date ? new Date(sprint.start_date).getTime() : NaN;
  const end = sprint.end_date ? new Date(sprint.end_date).getTime() : NaN;
  if (!Number.isNaN(start)) return start;
  if (!Number.isNaN(end)) return end;
  return Number.MIN_SAFE_INTEGER;
}

type SprintOrderState = Record<SprintStatusCategory, string[]>;

const createEmptySprintOrder = (): SprintOrderState => ({
  active: [],
  future: [],
  closed: [],
  other: [],
});

type SprintPlaceholderState = {
  category: SprintStatusCategory | null;
  targetSprintId: string | null;
  position: "before" | "after";
  atEnd: boolean;
};

// Removed verbose debug logging

/* ============================================================================
 * TASK CARD COMPONENT
 * ========================================================================= */

// Helper function to get status badge color classes
function getStatusColorClasses(status: string): string {
  const statusLower = status.toLowerCase().replace(/[\s_-]/g, '_');

  // Map common status names to color classes
  if (statusLower.includes('done') || statusLower.includes('completed') || statusLower.includes('closed') || statusLower.includes('resolved')) {
    return 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200';
  }
  if (statusLower.includes('in_progress') || statusLower.includes('inprogress') || statusLower.includes('working') || statusLower.includes('active')) {
    return 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200';
  }
  if (statusLower.includes('todo') || statusLower.includes('to_do') || statusLower.includes('open') || statusLower.includes('new')) {
    return 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200';
  }
  if (statusLower.includes('blocked') || statusLower.includes('waiting')) {
    return 'bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200';
  }
  if (statusLower.includes('review') || statusLower.includes('testing') || statusLower.includes('qa')) {
    return 'bg-orange-100 dark:bg-orange-900 text-orange-800 dark:text-orange-200';
  }
  if (statusLower.includes('backlog')) {
    return 'bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200';
  }

  // Default color
  return 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200';
}

function TaskCard({
  task,
  onClick,
  epic,
  isDragging
}: {
  task: Task;
  onClick: () => void;
  epic?: Epic;
  isDragging?: boolean;
}) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({
    id: `task-${task.id}`,
    data: { type: 'task', task }
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      className="group flex items-start gap-2 p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-md hover:border-gray-300 dark:hover:border-gray-600 transition-all cursor-pointer"
    >
      <div
        {...listeners}
        className="mt-0.5 cursor-grab active:cursor-grabbing text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
      >
        <GripVertical className="w-4 h-4" />
      </div>
      <div className="flex-1 min-w-0" onClick={onClick}>
        <div className="flex items-start justify-between gap-2 mb-1">
          <div className="text-sm font-medium text-gray-900 dark:text-white line-clamp-2 flex-1">
            {task.title}
          </div>
          <div className="flex items-center gap-1.5 shrink-0">
            {task.status && (
              <span className={`px-2 py-0.5 text-xs font-medium rounded ${getStatusColorClasses(task.status)}`}>
                {task.status}
              </span>
            )}
            {task.priority && (
              <span className={`px-2 py-0.5 text-xs font-medium rounded ${task.priority === "high" || task.priority === "highest" || task.priority === "critical"
                ? "bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200"
                : task.priority === "medium"
                  ? "bg-orange-100 dark:bg-orange-900 text-orange-800 dark:text-orange-200"
                  : "bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200"
                }`}>
                {task.priority}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {epic && (
            <span className="px-2 py-0.5 text-xs font-medium rounded flex items-center gap-1 bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200">
              {epic.color && <div className={`w-2 h-2 rounded-full ${epic.color}`}></div>}
              <span className="truncate max-w-[100px]">{epic.name}</span>
            </span>
          )}
          {task.assigned_to && (
            <span className="text-xs text-gray-500 dark:text-gray-400">
              @{task.assigned_to}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

/* ============================================================================
 * EPIC CARD (Droppable)
 * ========================================================================= */

function EpicCard({
  epic,
  isSelected,
  taskCount,
  onClick,
  isOver
}: {
  epic: Epic;
  isSelected: boolean;
  taskCount: number;
  onClick: () => void;
  isOver?: boolean;
}) {
  const { setNodeRef } = useDroppable({
    id: `epic-${epic.id}`,
    data: { type: 'epic', epicId: epic.id }
  });

  return (
    <button
      ref={setNodeRef}
      onClick={onClick}
      className={`w-full text-left p-2 rounded transition-colors ${isSelected
        ? "bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-300"
        : isOver
          ? "bg-green-50 dark:bg-green-950 text-green-700 dark:text-green-300 ring-2 ring-green-400"
          : "hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
        }`}
    >
      <div className="flex items-center gap-2 mb-1">
        {epic.color && <div className={`w-3 h-3 rounded ${epic.color} shrink-0`}></div>}
        <span className="text-sm font-medium truncate flex-1">{epic.name}</span>
        <span className="text-xs text-gray-500 dark:text-gray-400">{taskCount}</span>
      </div>
    </button>
  );
}

/* ============================================================================
 * EPIC SIDEBAR
 * ========================================================================= */

function EpicSidebar({
  onEpicSelect,
  selectedEpic,
  tasks,
  projectId,
  onEpicCreate,
  overEpicId,
  isMobile
}: {
  onEpicSelect: (epicId: string | null) => void;
  selectedEpic: string | null;
  tasks: Task[];
  projectId: string | null | undefined;
  onEpicCreate?: () => void;
  overEpicId?: string | null;
  isMobile?: boolean;
}) {
  const { epics, loading: epicsLoading } = useEpics(projectId);
  const [isOpen, setIsOpen] = useState(false);

  const epicCounts = useMemo(() => {
    const counts = new Map<string, number>();
    tasks.forEach(task => {
      if (task.epic_id) {
        counts.set(task.epic_id, (counts.get(task.epic_id) || 0) + 1);
      }
    });
    return counts;
  }, [tasks]);

  const tasksWithoutEpic = useMemo(() => {
    return tasks.filter(t => !t.epic_id).length;
  }, [tasks]);

  const { setNodeRef: setNoEpicRef } = useDroppable({
    id: 'no-epic',
    data: { type: 'no-epic' }
  });

  return (
    <div className={`${isMobile ? 'w-full border-b' : 'w-64 border-r'} bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 flex flex-col overflow-hidden`}>
      <div
        className="p-4 flex items-center justify-between cursor-pointer lg:cursor-default"
        onClick={() => isMobile && setIsOpen(!isOpen)}
      >
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider flex items-center gap-2">
          {isMobile && (isOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />)}
          EPICS
        </h3>
        {!isMobile && <CreateEpicDialog projectId={projectId} onEpicCreated={onEpicCreate} className="w-auto" />}
        {isMobile && !isOpen && (
          <span className="text-xs text-gray-500 bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded-full">
            {epics.length} epics
          </span>
        )}
      </div>

      {(isOpen || !isMobile) && (
        <div className="flex-1 flex flex-col overflow-hidden">
          {isMobile && (
            <div className="px-4 pb-2 border-b border-gray-100 dark:border-gray-800">
              <CreateEpicDialog projectId={projectId} onEpicCreated={onEpicCreate} />
            </div>
          )}
          <div className="flex-1 overflow-y-auto p-2">
            <button
              onClick={() => onEpicSelect(null)}
              className={`w-full text-left p-2.5 rounded-xl mb-2 transition-all duration-200 ${selectedEpic === null
                ? "bg-blue-600 shadow-md shadow-blue-500/20 text-white"
                : "hover:bg-gray-100 dark:hover:bg-gray-700/50 text-gray-700 dark:text-gray-300"
                }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold">All issues</span>
                <span className={cn("text-xs px-2 py-0.5 rounded-full",
                  selectedEpic === null ? "bg-white/20 text-white" : "bg-gray-100 dark:bg-gray-800 text-gray-500"
                )}>
                  {tasks.length}
                </span>
              </div>
            </button>

            {epicsLoading ? (
              <div className="p-2 text-sm text-gray-500 dark:text-gray-400">
                Loading epics...
              </div>
            ) : epics.length > 0 ? (
              <div className="space-y-1">
                {epics.map((epic) => (
                  <EpicCard
                    key={epic.id}
                    epic={epic}
                    isSelected={selectedEpic === epic.id}
                    taskCount={epicCounts.get(epic.id) || 0}
                    onClick={() => onEpicSelect(epic.id)}
                    isOver={overEpicId === epic.id}
                  />
                ))}
              </div>
            ) : (
              <div className="p-2 text-sm text-gray-500 dark:text-gray-400">
                No epics found
              </div>
            )}

            {tasksWithoutEpic > 0 && (
              <div className="mt-6 pt-4 border-t border-gray-100 dark:border-gray-800">
                <div
                  ref={setNoEpicRef}
                  className={`p-3 text-xs rounded-xl transition-all duration-200 flex items-center gap-2 ${overEpicId === 'no-epic'
                    ? "bg-orange-50 dark:bg-orange-950/40 text-orange-700 dark:text-orange-400 ring-2 ring-orange-400/30"
                    : "bg-gray-50/50 dark:bg-gray-900/30 text-gray-500 dark:text-gray-400"
                    }`}
                >
                  <div className="w-1.5 h-1.5 rounded-full bg-orange-400" />
                  <span className="font-medium">
                    {tasksWithoutEpic} {tasksWithoutEpic === 1 ? 'issue' : 'issues'} without epic
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* ============================================================================
 * SPRINT SECTION
 * ========================================================================= */

interface SprintSectionProps {
  sprint: SprintSummary;
  tasks: Task[];
  onTaskClick: (task: Task) => void;
  epicsMap?: Map<string, Epic>;
  isOver?: boolean;
  draggedTaskId?: string | null;
  dragHandleProps?: {
    attributes?: DraggableAttributes;
    listeners?: SyntheticListenerMap;
  };
  isSorting?: boolean;
  onAddTask?: (sprintId: string) => void;
  loading?: boolean;
}

function SprintSection({
  sprint,
  tasks,
  onTaskClick,
  epicsMap,
  isOver,
  draggedTaskId,
  dragHandleProps,
  isSorting,
  onAddTask,
  loading = false
}: SprintSectionProps) {
  const isActive = sprint.status === "active";
  const isClosed = sprint.status === "closed";
  const isFuture = sprint.status === "future";

  // Sprints should be collapsed by default for performance
  const [isExpanded, setIsExpanded] = useState(false);

  const { setNodeRef } = useDroppable({
    id: `sprint-${sprint.id}`,
    data: { type: 'sprint', sprintId: sprint.id }
  });

  const taskIds = useMemo(() => tasks.map((t: Task) => `task-${t.id}`), [tasks]);

  return (
    <div className={`mb-4 ${isSorting ? "opacity-80" : ""}`}>
      <div
        className={`p-3 rounded-t-lg border ${isActive
          ? "bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800"
          : isClosed
            ? "bg-gray-50 dark:bg-gray-900 border-gray-200 dark:border-gray-700"
            : isFuture
              ? "bg-purple-50 dark:bg-purple-950 border-purple-200 dark:border-purple-800"
              : "bg-gray-50 dark:bg-gray-900 border-gray-200 dark:border-gray-700"
          }`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            {dragHandleProps && (
              <button
                type="button"
                aria-label="Drag to reorder sprint"
                onPointerDown={(event) => event.stopPropagation()}
                className="shrink-0 text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-200 cursor-grab active:cursor-grabbing"
                {...dragHandleProps.attributes}
                {...dragHandleProps.listeners}
              >
                <GripVertical className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="shrink-0 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            >
              {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            </button>
            <h3 className="font-semibold text-gray-900 dark:text-white truncate">{sprint.name}</h3>
            {isActive && (
              <span className="px-2 py-0.5 text-xs font-medium rounded bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 shrink-0">
                Active
              </span>
            )}
            {isClosed && (
              <span className="px-2 py-0.5 text-xs font-medium rounded bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 shrink-0">
                Closed
              </span>
            )}
            {isFuture && (
              <span className="px-2 py-0.5 text-xs font-medium rounded bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200 shrink-0">
                Future
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 shrink-0">
            {sprint.start_date && sprint.end_date && (
              <div className="flex items-center gap-1 text-xs text-gray-600 dark:text-gray-400">
                <Calendar className="w-3 h-3" />
                <span>{new Date(sprint.start_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
                <span>-</span>
                <span>{new Date(sprint.end_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
              </div>
            )}
            <span className="px-2 py-1 bg-white dark:bg-gray-800 rounded text-xs font-medium text-gray-700 dark:text-gray-300 min-w-[30px] flex items-center justify-center">
              {loading ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin text-gray-400" />
              ) : (
                tasks.length
              )}
            </span>
          </div>
        </div>
      </div>

      {isExpanded && (
        <div
          ref={setNodeRef}
          className={`p-3 rounded-b-lg border-x border-b transition-colors ${isOver
            ? "border-blue-400 bg-blue-50/50 dark:bg-blue-950/50 border-2"
            : "border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900"
            }`}
        >
          {tasks.length === 0 ? (
            <div className="text-center py-8 text-sm text-gray-500 dark:text-gray-400">
              {isOver ? (
                <div className="border-2 border-dashed border-blue-400 bg-blue-50 dark:bg-blue-900/40 rounded-lg p-4 text-blue-600 dark:text-blue-300 font-medium">
                  Drop task here
                </div>
              ) : (
                <>
                  <p className="mb-2">No tasks in this sprint</p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onAddTask?.(sprint.id)}
                  >
                    <Plus className="w-4 h-4 mr-1" />
                    Add task
                  </Button>
                </>
              )}
            </div>
          ) : (
            <SortableContext items={taskIds} strategy={verticalListSortingStrategy}>
              <div className="space-y-2">
                {tasks.map((task, index) => (
                  <TaskCard
                    key={task.id}
                    task={task}
                    onClick={() => onTaskClick(task)}
                    epic={task.epic_id && epicsMap ? epicsMap.get(task.epic_id) : undefined}
                    isDragging={draggedTaskId === task.id}
                  />
                ))}
              </div>
            </SortableContext>
          )}
        </div>
      )}
    </div>
  );
}

/* ============================================================================
 * BACKLOG SECTION
 * ========================================================================= */

function BacklogSection({
  tasks,
  onTaskClick,
  epicsMap,
  isOver,
  draggedTaskId
}: {
  tasks: Task[];
  onTaskClick: (task: Task) => void;
  epicsMap?: Map<string, Epic>;
  isOver?: boolean;
  draggedTaskId?: string | null;
}) {
  const [isExpanded, setIsExpanded] = useState(true);

  const { setNodeRef } = useDroppable({
    id: "backlog",
    data: { type: 'backlog' }
  });

  const taskIds = useMemo(() => tasks.map((t: Task) => `task-${t.id}`), [tasks]);

  return (
    <div className="mb-4">
      <div className="p-3 bg-gray-100 dark:bg-gray-800 rounded-t-lg border border-gray-300 dark:border-gray-600">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="shrink-0 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            >
              {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            </button>
            <h3 className="font-semibold text-gray-900 dark:text-white">Backlog</h3>
          </div>
          <span className="px-2 py-1 bg-white dark:bg-gray-700 rounded text-xs font-medium text-gray-700 dark:text-gray-300">
            {tasks.length}
          </span>
        </div>
      </div>

      {isExpanded && (
        <div
          ref={setNodeRef}
          className={`p-3 rounded-b-lg border-x border-b transition-colors min-h-[200px] ${isOver
            ? "border-blue-400 bg-blue-50/50 dark:bg-blue-950/50 border-2"
            : "border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900"
            }`}
        >
          {tasks.length === 0 ? (
            <div className="text-center py-12 text-sm text-gray-500 dark:text-gray-400">
              {isOver ? (
                <div className="border-2 border-dashed border-blue-400 bg-blue-50 dark:bg-blue-900/40 rounded-lg p-6 text-blue-600 dark:text-blue-300 font-medium">
                  Drop here to remove from sprint
                </div>
              ) : (
                <p>No tasks in backlog</p>
              )}
            </div>
          ) : (
            <SortableContext items={taskIds} strategy={verticalListSortingStrategy}>
              <div className="space-y-2">
                {tasks.map((task) => (
                  <TaskCard
                    key={task.id}
                    task={task}
                    onClick={() => onTaskClick(task)}
                    epic={task.epic_id && epicsMap ? epicsMap.get(task.epic_id) : undefined}
                    isDragging={draggedTaskId === task.id}
                  />
                ))}
              </div>
            </SortableContext>
          )}
        </div>
      )}
    </div>
  );
}

/* ============================================================================
 * MAIN BACKLOG VIEW
 * ========================================================================= */

export function BacklogView() {
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [priorityFilter, setPriorityFilter] = useState<string>("all");
  const [selectedEpic, setSelectedEpic] = useState<string | null>(null);
  const [dragState, setDragState] = useState<DragState>({ type: null, id: null });
  const [overSprintId, setOverSprintId] = useState<string | null>(null);
  const [overTaskId, setOverTaskId] = useState<string | null>(null);
  const [overEpicId, setOverEpicId] = useState<string | null>(null);
  const [sprintCategoryOverrides, setSprintCategoryOverrides] = useState<Record<string, SprintStatusCategory>>({});
  const [sprintPlaceholder, setSprintPlaceholder] = useState<SprintPlaceholderState>({
    category: null,
    targetSprintId: null,
    position: "after",
    atEnd: false,
  });
  const [overSprintCategory, setOverSprintCategory] = useState<SprintStatusCategory | null>(null);
  const [createTaskDialogOpen, setCreateTaskDialogOpen] = useState(false);
  const [createTaskSprintId, setCreateTaskSprintId] = useState<string | null>(null);
  const [isSavingTask, setIsSavingTask] = useState(false);
  const [createTaskForm, setCreateTaskForm] = useState({
    title: "",
    description: "",
    status: "",
    priority: "",
  });
  const lastSprintHoverIdRef = useRef<string | null>(null);
  const lastSprintCategoryRef = useRef<SprintStatusCategory | null>(null);
  const { activeProjectId, activeProject, projectIdForData: projectIdForSprints } = useProjectData();
  const { state: loadingState, setTasksState } = usePMLoading();

  const [isMobile, setIsMobile] = useState(false);

  // Detect mobile
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 1024);
    };
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  useEffect(() => {
    setSearchQuery("");
    setStatusFilter("all");
    setPriorityFilter("all");
    setSelectedEpic(null);
  }, [activeProject?.id, projectIdForSprints]);

  const shouldLoadTasks = loadingState.canLoadTasks && projectIdForSprints;
  const { tasks: allTasks, loading, isFetching, error, refresh: refreshTasks } = useTasks(projectIdForSprints ?? undefined);

  const normalizedTasksForFiltering = useMemo<Task[]>(() => {
    if (!allTasks) return [];
    return allTasks.map((task) => ({
      ...task,
      sprint_id: task.sprint_id ?? null,
    })) as Task[];
  }, [allTasks]);

  useEffect(() => {
    if (shouldLoadTasks) {
      setTasksState({ loading, error, data: allTasks });
    } else if (!projectIdForSprints) {
      setTasksState({ loading: false, error: null, data: null });
    }
  }, [shouldLoadTasks, loading, error, allTasks, setTasksState, projectIdForSprints]);

  const { tasks } = useTaskFiltering({
    allTasks: normalizedTasksForFiltering,
    projectId: projectIdForSprints,
    activeProject,
    loading,
  });

  const { sprints, loading: sprintsLoading } = useSprints(projectIdForSprints ?? "", undefined);
  const { state: pmLoadingState } = usePMLoading();
  const projects = pmLoadingState.filterData.projects.data;

  useEffect(() => {
    if (!sprints) return;
    const ids = new Set(sprints.map((s) => s.id));
    setSprintCategoryOverrides((previous) => {
      const next = { ...previous };
      let changed = false;
      Object.keys(next).forEach((id) => {
        if (!ids.has(id)) {
          delete next[id];
          changed = true;
        }
      });
      return changed ? next : previous;
    });
  }, [sprints]);

  const resolveSprintCategory = useCallback(
    (sprint: SprintSummary): SprintStatusCategory => {
      return sprintCategoryOverrides[sprint.id] ?? getSprintStatusCategory(sprint.status);
    },
    [sprintCategoryOverrides]
  );
  const { epics } = useEpics(projectIdForSprints ?? undefined);
  const { statuses: availableStatusesFromBackend } = useStatuses(projectIdForSprints ?? undefined, "task");
  const { priorities: availablePrioritiesFromBackend } = usePriorities(projectIdForSprints ?? undefined);
  const [sprintOrder, setSprintOrder] = useState<SprintOrderState>(() => createEmptySprintOrder());

  const epicsMap = useMemo(() => {
    const map = new Map<string, Epic>();
    epics.forEach(epic => map.set(epic.id, epic));
    return map;
  }, [epics]);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    })
  );

  const handleTaskClick = (task: Task) => {
    setSelectedTask(task);
    setIsModalOpen(true);
  };

  const handleUpdateTask = useCallback(async (taskId: string, updates: Partial<Task>) => {
    if (!projectIdForSprints) throw new Error("Project ID is required");

    const url = new URL(resolveServiceURL(`pm/tasks/${taskId}`));
    url.searchParams.set('project_id', projectIdForSprints);

    const response = await fetch(url.toString(), {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('[handleUpdateTask] Error response:', errorText);
      throw new Error(errorText || `Failed to update task: ${response.status}`);
    }

    const result = await response.json();

    if (selectedTask && selectedTask.id === taskId) {
      setSelectedTask({ ...selectedTask, ...result });
    }

    // Trigger full refresh using the same event as sprint assignment
    window.dispatchEvent(new CustomEvent("pm_refresh", { detail: { type: "pm_refresh" } }));
    return result;
  }, [projectIdForSprints, selectedTask]);

  const handleAssignTaskToSprint = useCallback(async (taskId: string, sprintId: string) => {
    if (!projectIdForSprints) throw new Error('No project selected');

    const url = resolveServiceURL(`pm/projects/${projectIdForSprints}/tasks/${taskId}/assign-sprint`);
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sprint_id: sprintId }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `Failed to assign task: ${response.status}`);
    }

    window.dispatchEvent(new CustomEvent("pm_refresh", { detail: { type: "pm_refresh" } }));
  }, [projectIdForSprints]);

  const availableStatuses = useMemo(() => {
    if (availableStatusesFromBackend && availableStatusesFromBackend.length > 0) {
      return availableStatusesFromBackend.map(status => ({
        value: status.name.toLowerCase(),
        label: status.name
      }));
    }
    const statusMap = new Map<string, string>();
    tasks.forEach(task => {
      if (task.status) {
        const lower = task.status.toLowerCase();
        if (!statusMap.has(lower)) {
          statusMap.set(lower, task.status);
        }
      }
    });
    return Array.from(statusMap.entries()).map(([value, label]) => ({
      value,
      label
    }));
  }, [availableStatusesFromBackend, tasks]);

  const availablePriorities = useMemo(() => {
    if (availablePrioritiesFromBackend && availablePrioritiesFromBackend.length > 0) {
      return availablePrioritiesFromBackend.map(priority => ({
        value: priority.name.toLowerCase(),
        label: priority.name
      }));
    }
    const priorityMap = new Map<string, string>();
    tasks.forEach(task => {
      if (task.priority) {
        const lower = task.priority.toLowerCase();
        if (!priorityMap.has(lower)) {
          priorityMap.set(lower, task.priority);
        }
      }
    });
    return Array.from(priorityMap.entries()).map(([value, label]) => ({
      value,
      label
    }));
  }, [availablePrioritiesFromBackend, tasks]);

  const defaultStatusValue = useMemo(() => {
    if (availableStatuses.length === 0) return "todo";
    const todo = availableStatuses.find(status => status.value === "todo");
    return todo?.value ?? availableStatuses[0]?.value ?? "todo";
  }, [availableStatuses]);

  const defaultPriorityValue = useMemo(() => {
    if (availablePriorities.length === 0) return "medium";
    const medium = availablePriorities.find(priority => priority.value === "medium");
    return medium?.value ?? availablePriorities[0]?.value ?? "medium";
  }, [availablePriorities]);

  const resetCreateTaskState = useCallback(() => {
    setCreateTaskDialogOpen(false);
    setCreateTaskSprintId(null);
    setCreateTaskForm({
      title: "",
      description: "",
      status: defaultStatusValue,
      priority: defaultPriorityValue,
    });
    setIsSavingTask(false);
  }, [defaultPriorityValue, defaultStatusValue]);

  useEffect(() => {
    // keep defaults in sync when provider data changes
    setCreateTaskForm(prev => ({
      ...prev,
      status: prev.status || defaultStatusValue,
      priority: prev.priority || defaultPriorityValue,
    }));
  }, [defaultPriorityValue, defaultStatusValue]);

  const handleOpenCreateTaskDialog = useCallback((sprintId: string) => {
    if (!projectIdForSprints) {
      toast.error("Select a project before adding tasks.");
      return;
    }

    setCreateTaskSprintId(sprintId);
    setCreateTaskForm({
      title: "",
      description: "",
      status: defaultStatusValue,
      priority: defaultPriorityValue,
    });
    setCreateTaskDialogOpen(true);
  }, [defaultPriorityValue, defaultStatusValue, projectIdForSprints]);

  const handleConfirmCreateTask = useCallback(async () => {
    if (!projectIdForSprints) {
      toast.error("Select a project before adding tasks.");
      return;
    }
    if (!createTaskSprintId) {
      toast.error("Sprint context missing for new task.");
      return;
    }
    const trimmedTitle = createTaskForm.title.trim();
    if (!trimmedTitle) {
      toast.error("Task title is required.", { description: "Please enter a title before creating the task." });
      return;
    }

    setIsSavingTask(true);
    try {
      const response = await fetch(resolveServiceURL(`pm/projects/${projectIdForSprints}/tasks`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: trimmedTitle,
          description: createTaskForm.description,
          priority: createTaskForm.priority ?? undefined,
          status: createTaskForm.status ?? undefined,
          sprint_id: createTaskSprintId,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || `Failed to create task (status ${response.status})`);
      }

      await refreshTasks();
      window.dispatchEvent(new CustomEvent("pm_refresh", { detail: { type: "pm_refresh" } }));
      toast.success("Task created", {
        description: "A new task was added to the sprint.",
      });
      resetCreateTaskState();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      console.error("Failed to create task:", error);
      toast.error("Failed to create task", { description: message });
      setIsSavingTask(false);
    }
  }, [
    createTaskForm.description,
    createTaskForm.priority,
    createTaskForm.status,
    createTaskForm.title,
    createTaskSprintId,
    projectIdForSprints,
    refreshTasks,
    resetCreateTaskState,
  ]);

  const handleMoveTaskToBacklog = useCallback(async (taskId: string) => {
    if (!projectIdForSprints) throw new Error('No project selected');

    const url = resolveServiceURL(`pm/projects/${projectIdForSprints}/tasks/${taskId}/move-to-backlog`);
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `Failed to move to backlog: ${response.status}`);
    }

    window.dispatchEvent(new CustomEvent("pm_refresh", { detail: { type: "pm_refresh" } }));
  }, [projectIdForSprints]);


  // Filter tasks
  const filteredTasks = useMemo(() => {
    if (loading && (!tasks || tasks.length === 0)) return [];
    if (!tasks || tasks.length === 0) return [];

    let filtered = [...tasks];

    const trimmedQuery = (searchQuery ?? "").trim();
    if (trimmedQuery) {
      const query = trimmedQuery.toLowerCase();
      filtered = filtered.filter(t => {
        const title = (t.title ?? "").toLowerCase();
        const description = (t.description ?? "").toLowerCase();
        return title.includes(query) || description.includes(query);
      });
    }

    if (statusFilter && statusFilter !== "all") {
      const filterStatusLower = statusFilter.toLowerCase();
      filtered = filtered.filter(t => (t.status ?? "").toLowerCase() === filterStatusLower);
    }

    if (priorityFilter && priorityFilter !== "all") {
      const filterPriorityLower = priorityFilter.toLowerCase();
      filtered = filtered.filter(t => (t.priority ?? "").toLowerCase() === filterPriorityLower);
    }

    return filtered;
  }, [tasks, searchQuery, statusFilter, priorityFilter, loading]);

  const epicFilteredTasks = useMemo(() => {
    if (loading && (!filteredTasks || filteredTasks.length === 0)) return [];
    if (!filteredTasks || filteredTasks.length === 0) return [];
    if (!selectedEpic || selectedEpic === "all") return filteredTasks;
    return filteredTasks.filter(task => task.epic_id === selectedEpic);
  }, [filteredTasks, selectedEpic, loading]);

  useEffect(() => {
    if (!sprints || sprints.length === 0) {
      setSprintOrder(createEmptySprintOrder());
      // Removed debug logging
      return;
    }

    setSprintOrder((previous) => {
      // Removed debug logging

      const grouped: Record<SprintStatusCategory, SprintSummary[]> = {
        active: [],
        future: [],
        closed: [],
        other: [],
      };

      sprints.forEach((sprint) => {
        const category = resolveSprintCategory(sprint);
        grouped[category].push(sprint);
      });

      const next: SprintOrderState = {
        active: [],
        future: [],
        closed: [],
        other: [],
      };

      let changed = false;

      ORDERED_STATUS_CATEGORIES.forEach((category) => {
        const sortedIds = grouped[category]
          .sort((a, b) => getSprintTimestamp(b) - getSprintTimestamp(a))
          .map((s) => s.id);

        const existingOrder = previous[category] ?? [];
        const preserved = existingOrder.filter((id) => sortedIds.includes(id));
        const missing = sortedIds.filter((id) => !preserved.includes(id));
        const combined = [...preserved, ...missing];

        if (
          combined.length !== existingOrder.length ||
          combined.some((id, index) => id !== existingOrder[index])
        ) {
          changed = true;
          // Removed debug logging
        }

        next[category] = combined;
      });

      return changed ? next : previous;
    });
  }, [sprints, resolveSprintCategory]);

  const orderedSprints = useMemo(() => {
    if (!sprints || sprints.length === 0) return [];

    const grouped: Record<SprintStatusCategory, SprintSummary[]> = {
      active: [],
      future: [],
      closed: [],
      other: [],
    };

    sprints.forEach((sprint) => {
      const category = resolveSprintCategory(sprint);
      grouped[category].push(sprint);
    });

    const result: SprintSummary[] = [];

    ORDERED_STATUS_CATEGORIES.forEach((category) => {
      const idsOrder = sprintOrder[category] ?? [];
      const indexMap = new Map(idsOrder.map((id, index) => [id, index]));

      const sortedGroup = grouped[category].sort((a, b) => {
        const indexA = indexMap.has(a.id) ? indexMap.get(a.id)! : Number.MAX_SAFE_INTEGER;
        const indexB = indexMap.has(b.id) ? indexMap.get(b.id)! : Number.MAX_SAFE_INTEGER;

        if (indexA !== indexB) {
          return indexA - indexB;
        }

        return getSprintTimestamp(b) - getSprintTimestamp(a);
      });

      result.push(...sortedGroup);
    });

    return result;
  }, [sprints, sprintOrder, resolveSprintCategory]);

  const activeSprints = useMemo(
    () => orderedSprints.filter((sprint) => resolveSprintCategory(sprint) === "active"),
    [orderedSprints, resolveSprintCategory]
  );
  const futureSprints = useMemo(
    () => orderedSprints.filter((sprint) => resolveSprintCategory(sprint) === "future"),
    [orderedSprints, resolveSprintCategory]
  );
  const closedSprints = useMemo(
    () => orderedSprints.filter((sprint) => resolveSprintCategory(sprint) === "closed"),
    [orderedSprints, resolveSprintCategory]
  );
  const otherSprints = useMemo(
    () => orderedSprints.filter((sprint) => resolveSprintCategory(sprint) === "other"),
    [orderedSprints, resolveSprintCategory]
  );

  const tasksInSprints = useMemo(() => {
    const grouped: Record<string, Task[]> = {};
    const sprintSource = orderedSprints.length > 0 ? orderedSprints : sprints;

    // Helper to extract short ID from composite ID (e.g., "provider:7" -> "7")
    const extractShortId = (id: string | null | undefined): string | null => {
      if (!id) return null;
      const str = String(id);
      return str.includes(':') ? str.split(':').pop() || str : str;
    };

    sprintSource.forEach((sprint) => {
      const sprintShortId = extractShortId(sprint.id);
      grouped[sprint.id] = epicFilteredTasks.filter((task) => {
        const taskSprintShortId = extractShortId(task.sprint_id);
        // Match by exact composite ID OR by short ID
        return task.sprint_id === sprint.id ||
          String(task.sprint_id) === String(sprint.id) ||
          (taskSprintShortId && sprintShortId && taskSprintShortId === sprintShortId);
      });
    });
    return grouped;
  }, [orderedSprints, sprints, epicFilteredTasks]);

  const backlogTasks = useMemo(() => {
    const sprintSource = orderedSprints.length > 0 ? orderedSprints : sprints;
    const sprintIds = new Set(sprintSource.map((s) => s.id));
    // Also build a set of short IDs for comparison
    const sprintShortIds = new Set(sprintSource.map((s) => {
      const id = String(s.id);
      return id.includes(':') ? id.split(':').pop() || id : id;
    }));

    return epicFilteredTasks.filter((task) => {
      if (!task.sprint_id) return true;
      const taskSprintId = String(task.sprint_id);
      const taskSprintShortId = taskSprintId.includes(':')
        ? taskSprintId.split(':').pop() || taskSprintId
        : taskSprintId;
      // Task is in backlog if its sprint_id doesn't match any sprint (by full or short ID)
      return !sprintIds.has(task.sprint_id) &&
        !sprintIds.has(taskSprintId) &&
        !sprintShortIds.has(taskSprintShortId);
    });
  }, [orderedSprints, sprints, epicFilteredTasks]);

  const draggedTaskId = dragState.type === 'task' ? dragState.id : null;

  const draggedTask = useMemo(() => {
    if (!draggedTaskId) return null;
    return tasks.find((task) => String(task.id) === draggedTaskId);
  }, [draggedTaskId, tasks]);

  const isSprintDragging = dragState.type === 'sprint' && !!dragState.id;
  const activeSprintId = isSprintDragging ? dragState.id : null;

  const renderSprintsWithPlaceholder = useCallback(
    (
      categorySprints: SprintSummary[],
      category: SprintStatusCategory
    ) => {
      const nodes: ReactNode[] = [];

      const placeholderIndex = (() => {
        if (!isSprintDragging || sprintPlaceholder.category !== category) {
          return -1;
        }
        if (sprintPlaceholder.atEnd) {
          return categorySprints.length;
        }
        if (!sprintPlaceholder.targetSprintId) {
          return -1;
        }
        const targetIndex = categorySprints.findIndex(
          (s) => String(s.id) === sprintPlaceholder.targetSprintId
        );
        if (targetIndex === -1) {
          return sprintPlaceholder.position === "before" ? 0 : categorySprints.length;
        }
        return sprintPlaceholder.position === "before" ? targetIndex : targetIndex + 1;
      })();

      categorySprints.forEach((sprint, index) => {
        if (placeholderIndex === index) {
          nodes.push(<SprintDropPlaceholder key={`placeholder-${category}-${index}`} />);
        }

        nodes.push(
          <SortableSprintSection
            key={sprint.id}
            sprint={sprint}
            tasks={tasksInSprints[sprint.id] ?? []}
            onTaskClick={handleTaskClick}
            epicsMap={epicsMap}
            isOver={dragState.type !== 'sprint' && overSprintId === sprint.id}
            draggedTaskId={draggedTaskId}
            onAddTask={handleOpenCreateTaskDialog}
            loading={loading}
          />
        );
      });

      if (placeholderIndex === categorySprints.length) {
        nodes.push(<SprintDropPlaceholder key={`placeholder-${category}-end`} />);
      }

      return nodes;
    },
    [
      dragState.type,
      draggedTaskId,
      epicsMap,
      handleTaskClick,
      isSprintDragging,
      sprintPlaceholder,
      overSprintId,
      tasksInSprints,
      handleOpenCreateTaskDialog,
    ]
  );

  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event;
    const activeId = String(active.id);

    if (activeId.startsWith('task-')) {
      const taskId = activeId.replace('task-', '');
      const task = tasks.find(t => String(t.id) === taskId);
      const sourceSprintId = task?.sprint_id ? String(task.sprint_id) : null;
      // Removed debug logging
      setDragState({ type: 'task', id: taskId, sourceSprintId });
      return;
    }

    if (activeId.startsWith('sprint-')) {
      const sprintId = activeId.replace('sprint-', '');
      // Removed debug logging
      setDragState({ type: 'sprint', id: sprintId });
      lastSprintHoverIdRef.current = sprintId;
      const reference = (orderedSprints.length > 0 ? orderedSprints : sprints) ?? [];
      const sprint = reference.find((item) => String(item.id) === sprintId);
      const initialCategory = sprint ? resolveSprintCategory(sprint) : null;
      lastSprintCategoryRef.current = initialCategory;
      setOverSprintCategory(initialCategory);
      setSprintPlaceholder({
        category: initialCategory,
        targetSprintId: null,
        position: "after",
        atEnd: true,
      });
    }
  };

  const handleDragOver = (event: DragOverEvent) => {
    const { over } = event;
    if (!over) {
      setOverSprintId(null);
      setOverTaskId(null);
      setOverEpicId(null);
      // Removed debug logging
      return;
    }

    if (dragState.type !== 'sprint' && sprintPlaceholder.category !== null) {
      setSprintPlaceholder({
        category: null,
        targetSprintId: null,
        position: "after",
        atEnd: false,
      });
    }

    if (dragState.type === 'sprint') {
      const currentSprintId = dragState.id as string;
      const overId = String(over.id);
      const overData = over.data.current as
        | { sortable?: { containerId?: string } }
        | undefined;

      const reference = (orderedSprints.length > 0 ? orderedSprints : sprints) ?? [];
      const sourceSprintFull = reference.find((item) => String(item.id) === currentSprintId);
      const sourceCategory = sourceSprintFull ? resolveSprintCategory(sourceSprintFull) : null;

      const getCategoryIds = (category: SprintStatusCategory | null) => {
        if (!category) return [];
        return reference
          .filter((item) => resolveSprintCategory(item) === category)
          .map((item) => String(item.id));
      };

      const activeRect = (event.active?.rect?.current?.translated ??
        event.active?.rect?.current) as ClientRect | null;

      const pointerRelativePosition = (targetRect?: ClientRect | null): "before" | "after" => {
        if (!activeRect || !targetRect) return "after";
        const activeCenter = activeRect.top + activeRect.height / 2;
        const targetCenter = targetRect.top + targetRect.height / 2;
        return activeCenter <= targetCenter ? "before" : "after";
      };

      const computePosition = (
        targetId: string | null,
        category: SprintStatusCategory | null,
        targetRect?: ClientRect | null
      ): "before" | "after" => {
        if (!targetId || !category) return "after";
        const ids = getCategoryIds(category);
        const sourceIdx = ids.indexOf(currentSprintId);
        const targetIdx = ids.indexOf(targetId);
        if (sourceIdx === -1 || targetIdx === -1) {
          return pointerRelativePosition(targetRect);
        }
        if (!targetRect) {
          return targetIdx < sourceIdx ? "before" : "after";
        }
        if (sourceIdx > targetIdx) {
          return "before";
        }
        if (sourceIdx < targetIdx) {
          return pointerRelativePosition(targetRect);
        }
        return pointerRelativePosition(targetRect);
      };

      const resolveContainerSprintId = () => {
        const containerId = overData?.sortable?.containerId;
        if (containerId && containerId.startsWith("sprint-")) {
          return containerId.replace("sprint-", "");
        }
        return null;
      };

      const applyPlaceholder = (
        category: SprintStatusCategory | null,
        targetSprintId: string | null,
        atEnd = false,
        targetRect?: ClientRect | null
      ) => {
        const position = computePosition(targetSprintId, category, targetRect);
        setSprintPlaceholder({
          category,
          targetSprintId,
          position,
          atEnd,
        });
      };

      const setHoverSprint = (sprintId: string | null, targetRect?: ClientRect | null) => {
        setOverSprintId(sprintId);
        lastSprintHoverIdRef.current = sprintId;
        if (sprintId) {
          const targetSprint = reference.find((item) => String(item.id) === sprintId);
          const category = targetSprint ? resolveSprintCategory(targetSprint) : null;
          lastSprintCategoryRef.current = category ?? lastSprintCategoryRef.current ?? sourceCategory;
          setOverSprintCategory(category);
          applyPlaceholder(
            category ?? lastSprintCategoryRef.current ?? sourceCategory ?? null,
            sprintId,
            false,
            targetRect
          );
        } else {
          setOverSprintCategory(null);
          applyPlaceholder(null, null, false);
        }
      };

      if (overId.startsWith("sprint-")) {
        const targetSprintId = overId.replace("sprint-", "");
        setHoverSprint(targetSprintId, over.rect as ClientRect | null);
        // Removed debug logging
        const targetSprint = reference.find((item) => String(item.id) === targetSprintId);
        const category = targetSprint ? resolveSprintCategory(targetSprint) : null;

        if (targetSprintId === currentSprintId) {
          applyPlaceholder(
            category ?? sourceCategory ?? null,
            targetSprintId,
            false,
            over.rect as ClientRect | null
          );
          return;
        }

        applyPlaceholder(
          category ?? sourceCategory ?? null,
          targetSprintId,
          false,
          over.rect as ClientRect | null
        );
      } else if (overId.startsWith("task-")) {
        const taskId = overId.replace("task-", "");
        const task = tasks.find((t) => String(t.id) === taskId);
        const containerSprintId = task?.sprint_id
          ? String(task.sprint_id)
          : resolveContainerSprintId();
        setHoverSprint(containerSprintId, over.rect as ClientRect | null);
        // Removed debug logging
        if (containerSprintId) {
          const targetSprint = reference.find((item) => String(item.id) === containerSprintId);
          const category = targetSprint ? resolveSprintCategory(targetSprint) : null;
          applyPlaceholder(
            category ?? sourceCategory ?? null,
            containerSprintId,
            false,
            over.rect as ClientRect | null
          );
        }
      } else if (overId === "backlog") {
        setHoverSprint(null);
        // Removed debug logging
        applyPlaceholder(null, null, false);
      } else if (overId.startsWith("sprint-category-")) {
        const category = overId.replace("sprint-category-", "") as SprintStatusCategory;
        setHoverSprint(null);
        lastSprintCategoryRef.current = category;
        // Removed debug logging
        setOverSprintCategory(category);
        applyPlaceholder(category, null, true);
      } else {
        const containerSprintId = resolveContainerSprintId();
        if (containerSprintId) {
          setHoverSprint(containerSprintId, over.rect as ClientRect | null);
          // Removed debug logging
          const targetSprint = reference.find((item) => String(item.id) === containerSprintId);
          const category = targetSprint ? resolveSprintCategory(targetSprint) : null;
          applyPlaceholder(
            category ?? sourceCategory ?? null,
            containerSprintId,
            false,
            over.rect as ClientRect | null
          );
        } else {
          setHoverSprint(null);
          // Removed debug logging
          applyPlaceholder(null, null, false);
        }
      }
      setOverTaskId(null);
      setOverEpicId(null);
      return;
    }

    const overId = String(over.id);

    // Epic drop zone
    if (overId.startsWith('epic-')) {
      setOverEpicId(overId.replace('epic-', ''));
      setOverSprintId(null);
      setOverTaskId(null);
      // Removed debug logging
      return;
    }

    // No epic drop zone
    if (overId === 'no-epic') {
      setOverEpicId('no-epic');
      setOverSprintId(null);
      setOverTaskId(null);
      // Removed debug logging
      return;
    }

    // Direct drop zone
    if (overId.startsWith('sprint-')) {
      setOverSprintId(overId.replace('sprint-', ''));
      setOverTaskId(null);
      setOverEpicId(null);
      // Removed debug logging
      return;
    }

    if (overId === 'backlog') {
      setOverSprintId('backlog');
      setOverTaskId(null);
      setOverEpicId(null);
      // Removed debug logging
      return;
    }

    // If hovering over a task, find which sprint it belongs to
    if (overId.startsWith('task-')) {
      const taskId = overId.replace('task-', '');
      const task = tasks.find(t => String(t.id) === taskId);

      if (task) {
        setOverTaskId(taskId);
        setOverEpicId(null);
        if (task.sprint_id) {
          setOverSprintId(String(task.sprint_id));
          // Removed debug logging
        } else {
          setOverSprintId('backlog');
          // Removed debug logging
        }
        return;
      }
    }

    setOverSprintId(null);
    setOverTaskId(null);
    setOverEpicId(null);
    setOverSprintCategory(null);
    // Removed debug logging
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const { over } = event;
    const currentDragState = dragState;
    const previousOverSprintId = overSprintId ?? lastSprintHoverIdRef.current;
    const placeholderState = sprintPlaceholder;
    setDragState({ type: null, id: null });
    setOverSprintId(null);
    setOverTaskId(null);
    setOverEpicId(null);
    setOverSprintCategory(null);

    if (!over) {
      // Removed debug logging
      lastSprintCategoryRef.current = null;
      setOverSprintCategory(null);
      setSprintPlaceholder({
        category: null,
        targetSprintId: null,
        position: "after",
        atEnd: false,
      });
      return;
    }

    if (currentDragState.type === 'sprint' && currentDragState.id) {
      const overId = String(over.id);
      const overData = over.data.current as
        | { sortable?: { containerId?: string } }
        | undefined;
      let targetSprintId: string | null = null;
      let targetCategory: SprintStatusCategory | null = null;

      if (overId.startsWith("sprint-")) {
        targetSprintId = overId.replace("sprint-", "");
        lastSprintHoverIdRef.current = targetSprintId;
      } else if (overId.startsWith("task-")) {
        const taskId = overId.replace("task-", "");
        const task = tasks.find((t) => String(t.id) === taskId);
        targetSprintId = task?.sprint_id ? String(task.sprint_id) : null;
        if (!targetSprintId) {
          const containerId = overData?.sortable?.containerId;
          if (containerId && containerId.startsWith("sprint-")) {
            targetSprintId = containerId.replace("sprint-", "");
          }
        }
        if (targetSprintId) {
          // Removed debug logging
        }
      } else if (overId.startsWith("sprint-category-")) {
        targetCategory = overId.replace("sprint-category-", "") as SprintStatusCategory;
        lastSprintHoverIdRef.current = null;
        // Removed debug logging
      } else if (overId === "backlog") {
        targetSprintId = null;
        lastSprintHoverIdRef.current = null;
        lastSprintCategoryRef.current = null;
        // Removed debug logging
      } else if (previousOverSprintId) {
        targetSprintId = previousOverSprintId;
        // Removed debug logging
      } else if (lastSprintCategoryRef.current) {
        targetCategory = lastSprintCategoryRef.current;
        // Removed debug logging
      } else {
        // Removed debug logging
        return;
      }

      if (!targetSprintId && lastSprintHoverIdRef.current) {
        targetSprintId = lastSprintHoverIdRef.current;
      }
      if (!targetCategory && !targetSprintId) {
        const containerId = overData?.sortable?.containerId;
        if (containerId && containerId.startsWith("sprint-")) {
          targetSprintId = containerId.replace("sprint-", "");
          // Removed debug logging
        }
      }

      const orderedSource = orderedSprints.length > 0 ? orderedSprints : sprints;
      const sourceSprint = orderedSource.find((s) => String(s.id) === currentDragState.id);
      const targetSprint = targetSprintId
        ? orderedSource.find((s) => String(s.id) === targetSprintId)
        : null;

      if (!sourceSprint) {
        // Removed debug logging
        return;
      }

      if (targetSprintId === currentDragState.id && (!targetCategory || targetCategory === resolveSprintCategory(sourceSprint))) {
        // Removed debug logging
        return;
      }

      if (!targetSprint && !targetCategory) {
        // Removed debug logging
        return;
      }

      if (!targetCategory && targetSprint) {
        targetCategory = resolveSprintCategory(targetSprint);
      }

      if (!targetCategory && lastSprintCategoryRef.current) {
        targetCategory = lastSprintCategoryRef.current;
      }

      if (!targetCategory) {
        targetCategory = resolveSprintCategory(sourceSprint);
      }

      const resolvedSourceCategory = resolveSprintCategory(sourceSprint);
      let desiredCategory = targetCategory;
      const actualSourceCategory = getSprintStatusCategory(sourceSprint.status);

      if (placeholderState.category) {
        desiredCategory = placeholderState.category;
      }

      const placeholderTargetSprintId =
        placeholderState.targetSprintId && placeholderState.targetSprintId !== currentDragState.id
          ? placeholderState.targetSprintId
          : targetSprintId;
      const placeholderPosition = placeholderState.position;
      const placeholderAtEnd = placeholderState.atEnd;

      const activeSortable = (event.active.data.current as { sortable?: { index: number; containerId?: string } } | undefined)?.sortable;
      const overSortable = (over.data.current as { sortable?: { index: number; containerId?: string } } | undefined)?.sortable;
      const sameContainer =
        !!activeSortable?.containerId &&
        !!overSortable?.containerId &&
        activeSortable.containerId === overSortable.containerId;

      setSprintOrder((previous) => {
        const reference = (orderedSprints.length > 0 ? orderedSprints : sprints) ?? [];
        const categoryLists: Record<SprintStatusCategory, string[]> = {
          active: [],
          future: [],
          closed: [],
          other: [],
        };

        reference.forEach((sprint) => {
          const category = resolveSprintCategory(sprint);
          categoryLists[category] = [...categoryLists[category], sprint.id];
        });

        ORDERED_STATUS_CATEGORIES.forEach((category) => {
          categoryLists[category] = categoryLists[category].filter((id, index, arr) => arr.indexOf(id) === index);
        });

        const sourceList = categoryLists[resolvedSourceCategory].filter(
          (id, index, arr) => arr.indexOf(id) === index
        );
        if (!sourceList.includes(sourceSprint.id)) {
          sourceList.push(sourceSprint.id);
        }

        const sourceIndex = sourceList.indexOf(sourceSprint.id);

        if (desiredCategory === resolvedSourceCategory) {
          const filteredList = sourceList.filter((id) => id !== sourceSprint.id);

          let newIndex: number;

          if (placeholderAtEnd && placeholderState.category === resolvedSourceCategory) {
            newIndex = filteredList.length;
          } else if (placeholderTargetSprintId) {
            const targetIndex = filteredList.indexOf(placeholderTargetSprintId);
            if (targetIndex === -1) {
              newIndex = filteredList.length;
            } else {
              newIndex = placeholderPosition === "before" ? targetIndex : targetIndex + 1;
            }
          } else if (targetSprint && filteredList.includes(targetSprint.id)) {
            const targetIndex = filteredList.indexOf(targetSprint.id);
            if (
              sameContainer &&
              activeSortable &&
              typeof activeSortable.index === "number" &&
              activeSortable.index >= 0 &&
              overSortable &&
              typeof overSortable.index === "number" &&
              overSortable.index >= 0
            ) {
              const overIndex = overSortable.index;
              const activeIndex = activeSortable.index;
              if (placeholderTargetSprintId) {
                newIndex = placeholderPosition === "before" ? targetIndex : targetIndex + 1;
              } else if (sourceIndex > targetIndex) {
                newIndex = placeholderPosition === "before" ? targetIndex : targetIndex + 1;
              } else if (sourceIndex < targetIndex) {
                newIndex = placeholderPosition === "before" ? overIndex : overIndex + 1;
              } else {
                newIndex = placeholderPosition === "before" ? targetIndex : targetIndex + 1;
              }
            } else {
              newIndex = sourceIndex > targetIndex ? targetIndex : targetIndex + 1;
            }
          } else if (
            overSortable &&
            typeof overSortable.index === "number" &&
            overSortable.index >= 0
          ) {
            newIndex = placeholderPosition === "before" ? overSortable.index : overSortable.index + 1;
          } else {
            newIndex = filteredList.length;
          }

          const boundedIndex = Math.max(0, Math.min(newIndex, filteredList.length));
          filteredList.splice(boundedIndex, 0, sourceSprint.id);
          categoryLists[resolvedSourceCategory] = filteredList;
        } else {
          const cleanedSourceList = sourceList.filter((id) => id !== sourceSprint.id);
          categoryLists[resolvedSourceCategory] = cleanedSourceList;

          const targetList = categoryLists[desiredCategory].filter(
            (id, index, arr) => arr.indexOf(id) === index
          );
          let insertIndex: number;

          if (placeholderAtEnd || (!placeholderTargetSprintId && !targetSprint)) {
            insertIndex = targetList.length;
          } else if (placeholderTargetSprintId) {
            const targetIdx = targetList.indexOf(placeholderTargetSprintId);
            if (targetIdx === -1) {
              insertIndex = targetList.length;
            } else {
              insertIndex = placeholderPosition === "before" ? targetIdx : targetIdx + 1;
            }
          } else if (targetSprint) {
            const sortableIndex =
              overSortable && typeof overSortable.index === "number" && overSortable.index >= 0
                ? overSortable.index
                : targetList.indexOf(targetSprint.id);
            insertIndex = sortableIndex === -1 ? targetList.length : sortableIndex;
          } else {
            insertIndex = targetList.length;
          }

          const boundedIndex = Math.max(0, Math.min(insertIndex, targetList.length));
          const nextTargetList = [...targetList];
          nextTargetList.splice(boundedIndex, 0, sourceSprint.id);
          categoryLists[desiredCategory] = nextTargetList;
        }

        const next: SprintOrderState = {
          active: categoryLists.active,
          future: categoryLists.future,
          closed: categoryLists.closed,
          other: categoryLists.other,
        };

        const stateUnchanged = ORDERED_STATUS_CATEGORIES.every((category) => {
          const prevGroup = previous[category] ?? [];
          const nextGroup = next[category] ?? [];
          return (
            prevGroup.length === nextGroup.length &&
            prevGroup.every((id, index) => id === nextGroup[index])
          );
        });

        if (stateUnchanged) {
          // Removed debug logging
          return previous;
        }

        // Removed debug logging

        return next;
      });

      setSprintCategoryOverrides((previous) => {
        const next = { ...previous };
        if (desiredCategory === actualSourceCategory) {
          delete next[sourceSprint.id];
        } else {
          next[sourceSprint.id] = desiredCategory;
        }
        return next;
      });

      lastSprintHoverIdRef.current = null;
      lastSprintCategoryRef.current = null;
      setOverSprintCategory(null);
      setSprintPlaceholder({
        category: null,
        targetSprintId: null,
        position: "after",
        atEnd: false,
      });
      return;
    }

    if (currentDragState.type !== 'task' || !currentDragState.id) {
      // Removed debug logging
      return;
    }

    const overId = String(over.id);
    const taskId = currentDragState.id;
    const draggedTask = tasks.find(t => String(t.id) === taskId);
    if (!draggedTask) return;

    // Handle epic assignment
    if (overId.startsWith("epic-")) {
      const epicId = overId.replace("epic-", "");
      if (String(draggedTask.epic_id) === epicId) return; // Already in this epic

      try {
        await handleUpdateTask(taskId, { epic_id: epicId });
        toast.success("Task assigned to epic", {
          description: `${draggedTask.title} has been assigned to the epic.`
        });
        // Removed debug logging
      } catch (error) {
        console.error("Failed to assign task to epic:", error);
        toast.error("Failed to assign task to epic", {
          description: error instanceof Error ? error.message : "Unknown error"
        });
      }
      return;
    }

    // Handle epic removal (drop on "no-epic" zone)
    if (overId === "no-epic") {
      if (!draggedTask.epic_id) {
        return; // Already has no epic
      }

      try {
        // Use dedicated remove-epic endpoint
        const url = resolveServiceURL(`pm/projects/${projectIdForSprints}/tasks/${taskId}/remove-epic`);

        const response = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        });

        if (!response.ok) {
          const errorText = await response.text();
          console.error('[handleDragEnd] Remove epic error:', errorText);
          throw new Error(errorText || `Failed to remove epic: ${response.status}`);
        }

        await response.json();

        toast.success("Epic removed from task", {
          description: `${draggedTask.title} is no longer assigned to an epic.`
        });

        // Trigger full refresh
        window.dispatchEvent(new CustomEvent("pm_refresh", { detail: { type: "pm_refresh" } }));
      } catch (error) {
        console.error("Failed to remove task from epic:", error);
        toast.error("Failed to remove epic from task", {
          description: error instanceof Error ? error.message : "Unknown error"
        });
      }
      return;
    }

    let targetSprintId: string | null = null;

    // Determine target sprint
    if (overId === "backlog") {
      targetSprintId = null; // Moving to backlog
    } else if (overId.startsWith("sprint-")) {
      targetSprintId = overId.replace("sprint-", "");
    } else if (overId.startsWith("task-")) {
      // Dropped on another task - find which sprint it belongs to
      const targetTaskId = overId.replace("task-", "");
      const targetTask = tasks.find(t => String(t.id) === targetTaskId);
      if (targetTask) {
        targetSprintId = targetTask.sprint_id ? String(targetTask.sprint_id) : null;
      }
    }

    // Handle move to backlog
    if (targetSprintId === null) {
      if (!draggedTask.sprint_id) return; // Already in backlog
      try {
        await handleMoveTaskToBacklog(taskId);
        toast.success("Task moved to backlog", {
          description: `${draggedTask.title} has been moved to the backlog.`
        });
        // Removed debug logging
      } catch (error) {
        console.error("Failed to move task to backlog:", error);
        toast.error("Failed to move task to backlog", {
          description: error instanceof Error ? error.message : "Unknown error"
        });
      }
      return;
    }

    // Handle move to sprint
    if (String(draggedTask.sprint_id) === targetSprintId) return; // Already in this sprint

    try {
      await handleAssignTaskToSprint(taskId, targetSprintId);
      const targetSprint = sprints.find(s => String(s.id) === targetSprintId);
      toast.success("Task assigned to sprint", {
        description: `${draggedTask.title} has been assigned to ${targetSprint?.name || 'sprint'}.`
      });
      // Removed debug logging
    } catch (error) {
      console.error("Failed to assign task to sprint:", error);
      toast.error("Failed to assign task to sprint", {
        description: error instanceof Error ? error.message : "Unknown error"
      });
    }
  };

  const isLoading = loadingState.filterData.loading || (shouldLoadTasks && loading) || (shouldLoadTasks && isFetching);

  if (isLoading) {
    // Calculate loading progress
    const loadingItems = [
      { label: "Tasks", isLoading: loading, count: allTasks?.length || 0 },
      { label: "Sprints", isLoading: sprintsLoading, count: sprints?.length || 0 },
    ];
    const completedCount = loadingItems.filter(item => !item.isLoading).length;
    const progressPercent = Math.round((completedCount / loadingItems.length) * 100);

    return (
      <div className="h-full w-full flex items-center justify-center bg-muted/20 p-4">
        <div className="bg-card border rounded-xl shadow-lg p-5 w-full max-w-sm">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold flex items-center gap-2">
              <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                <Loader2 className="w-4 h-4 animate-spin text-blue-600 dark:text-blue-400" />
              </div>
              Loading Backlog
            </h3>
            <span className="text-xs font-mono text-muted-foreground">
              {progressPercent}%
            </span>
          </div>

          {/* Progress bar */}
          <div className="w-full h-1.5 bg-muted rounded-full mb-4 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${progressPercent}%` }}
            />
          </div>

          <div className="space-y-2">
            {loadingItems.map((item, index) => (
              <div key={index} className="flex items-center justify-between py-1.5 px-2 bg-muted/30 rounded-md">
                <div className="flex items-center gap-2">
                  {index === 0 ? <ListTodo className="w-3.5 h-3.5 text-green-500" /> : <Target className="w-3.5 h-3.5 text-purple-500" />}
                  <span className="text-xs font-medium">{item.label}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className={`text-xs font-mono tabular-nums ${item.isLoading ? 'text-blue-600 dark:text-blue-400' : 'text-green-600 dark:text-green-400'}`}>
                    {item.isLoading ? (item.count > 0 ? item.count : "...") : item.count}
                  </span>
                  {item.isLoading ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-500" />
                  ) : (
                    <div className="w-3.5 h-3.5 text-green-500">✓</div>
                  )}
                </div>
              </div>
            ))}
          </div>

          <p className="text-[10px] text-muted-foreground mt-3 text-center">
            Loading tasks and sprints...
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20 px-4">
        <div className="text-red-500 font-semibold mb-2">Error Loading Tasks</div>
        <div className="text-red-400 text-sm text-center max-w-2xl">{error.message}</div>
      </div>
    );
  }


  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
    >
      <div className={`flex h-full ${isMobile ? 'flex-col' : 'flex-row'}`}>
        {/* Left Sidebar - Epics */}
        <EpicSidebar
          onEpicSelect={setSelectedEpic}
          selectedEpic={selectedEpic}
          tasks={tasks}
          projectId={projectIdForSprints}
          onEpicCreate={() => {
            window.dispatchEvent(new CustomEvent("pm_refresh", { detail: { type: "pm_refresh" } }));
          }}
          overEpicId={overEpicId}
          isMobile={isMobile}
        />

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col overflow-hidden bg-gray-50 dark:bg-gray-900">
          {/* Top Header with Filters */}
          <div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
            <div className="mb-4">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Backlog</h2>
            </div>

            {/* Filters */}
            <div className="flex flex-col md:flex-row gap-3">
              <div className="flex-1">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <Input
                    type="text"
                    placeholder="Search tasks..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>
              {(availableStatuses.length > 0 || availablePriorities.length > 0) && (
                <div className="flex gap-2">
                  {availableStatuses.length > 0 && (
                    <Select value={statusFilter} onValueChange={setStatusFilter}>
                      <SelectTrigger className="w-[140px]">
                        <Filter className="w-4 h-4 mr-2" />
                        <SelectValue placeholder="Status" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Status</SelectItem>
                        {availableStatuses.map(({ value, label }) => (
                          <SelectItem key={value} value={value}>{label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                  {availablePriorities.length > 0 && (
                    <Select value={priorityFilter} onValueChange={setPriorityFilter}>
                      <SelectTrigger className="w-[140px]">
                        <SelectValue placeholder="Priority" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Priority</SelectItem>
                        {availablePriorities.map(({ value, label }) => (
                          <SelectItem key={value} value={value}>{label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Sprints and Backlog - Scrollable */}
          <div className="flex-1 overflow-y-auto p-6">
            {!activeProjectId ? (
              <Card className="p-6">
                <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                  {(projects && projects.length > 0) ? (
                    <div className="flex flex-col items-center gap-2">
                      <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
                      <span>Loading project...</span>
                    </div>
                  ) : (
                    "Please select a project to view sprints"
                  )}
                </div>
              </Card>
            ) : sprintsLoading ? (
              <Card className="p-6">
                <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                  Loading sprints...
                </div>
              </Card>
            ) : (
              <div className="max-w-5xl mx-auto">
                {/* Active sprints */}
                {(activeSprints.length > 0 || isSprintDragging) && (
                  <div className="mb-6">
                    <h2 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3 px-1">
                      Active Sprints
                    </h2>
                    {activeSprints.length > 0 ? (
                      <SortableContext
                        items={activeSprints.map((sprint) => `sprint-${sprint.id}`)}
                        strategy={verticalListSortingStrategy}
                      >
                        {renderSprintsWithPlaceholder(activeSprints, "active")}
                      </SortableContext>
                    ) : isSprintDragging ? (
                      overSprintCategory === "active" ? (
                        <SprintDropPlaceholder />
                      ) : (
                        <SprintCategoryDropZone
                          category="active"
                          title="No active sprints"
                          descriptionWhenIdle="There are currently no active sprints."
                          descriptionWhenDragging="Drop a sprint here to move it into the Active group."
                          isSprintDragging
                        />
                      )
                    ) : null}
                  </div>
                )}

                {/* Future sprints */}
                {(futureSprints.length > 0 || isSprintDragging) && (
                  <div className="mb-6">
                    <h2 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3 px-1">
                      Future Sprints
                    </h2>
                    {futureSprints.length > 0 ? (
                      <SortableContext
                        items={futureSprints.map((sprint) => `sprint-${sprint.id}`)}
                        strategy={verticalListSortingStrategy}
                      >
                        {renderSprintsWithPlaceholder(futureSprints, "future")}
                      </SortableContext>
                    ) : isSprintDragging ? (
                      overSprintCategory === "future" ? (
                        <SprintDropPlaceholder />
                      ) : (
                        <SprintCategoryDropZone
                          category="future"
                          title="No future sprints"
                          descriptionWhenIdle="There are no upcoming sprints scheduled."
                          descriptionWhenDragging="Drop a sprint here to plan it for the future."
                          isSprintDragging
                        />
                      )
                    ) : null}
                  </div>
                )}

                {/* Backlog */}
                <div className="mb-6">
                  <h2 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3 px-1">
                    Backlog
                  </h2>
                  <BacklogSection
                    tasks={backlogTasks}
                    onTaskClick={handleTaskClick}
                    epicsMap={epicsMap}
                    isOver={overSprintId === 'backlog'}
                    draggedTaskId={draggedTaskId}
                  />
                </div>

                {/* Closed sprints */}
                {(closedSprints.length > 0 || isSprintDragging) && (
                  <div className="mb-6">
                    <h2 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3 px-1">
                      Closed Sprints
                    </h2>
                    {closedSprints.length > 0 ? (
                      <SortableContext
                        items={closedSprints.map((sprint) => `sprint-${sprint.id}`)}
                        strategy={verticalListSortingStrategy}
                      >
                        {renderSprintsWithPlaceholder(closedSprints, "closed")}
                      </SortableContext>
                    ) : isSprintDragging ? (
                      overSprintCategory === "closed" ? (
                        <SprintDropPlaceholder />
                      ) : (
                        <SprintCategoryDropZone
                          category="closed"
                          title="No closed sprints"
                          descriptionWhenIdle="No sprints have been closed yet."
                          descriptionWhenDragging="Drop a sprint here to move it into the Closed group."
                          isSprintDragging
                        />
                      )
                    ) : null}
                  </div>
                )}

                {/* Other sprints */}
                {(otherSprints.length > 0 || isSprintDragging) && (
                  <div className="mb-6">
                    <h2 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3 px-1">
                      Other Sprints
                    </h2>
                    {otherSprints.length > 0 ? (
                      <SortableContext
                        items={otherSprints.map((sprint) => `sprint-${sprint.id}`)}
                        strategy={verticalListSortingStrategy}
                      >
                        {renderSprintsWithPlaceholder(otherSprints, "other")}
                      </SortableContext>
                    ) : isSprintDragging ? (
                      overSprintCategory === "other" ? (
                        <SprintDropPlaceholder />
                      ) : (
                        <SprintCategoryDropZone
                          category="other"
                          title="No uncategorized sprints"
                          descriptionWhenIdle="There are no sprints in the Other group."
                          descriptionWhenDragging="Drop a sprint here to move it into the Other group."
                          isSprintDragging
                        />
                      )
                    ) : null}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      <DragOverlay>
        {draggedTask ? (
          <div className="p-3 bg-white dark:bg-gray-800 rounded-lg border-2 border-blue-400 shadow-2xl opacity-95 max-w-md">
            <div className="font-medium text-sm text-gray-900 dark:text-white line-clamp-2">
              {draggedTask.title}
            </div>
            {draggedTask.priority && (
              <span className="inline-block mt-1 px-2 py-0.5 text-xs font-medium rounded bg-blue-100 text-blue-800">
                {draggedTask.priority}
              </span>
            )}
          </div>
        ) : null}
      </DragOverlay>

      <Dialog
        open={createTaskDialogOpen}
        onOpenChange={(open) => {
          if (!open) {
            if (isSavingTask) {
              return;
            }
            resetCreateTaskState();
          } else {
            setCreateTaskDialogOpen(true);
          }
        }}
      >
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Create Task</DialogTitle>
          </DialogHeader>
          <div className="space-y-5 py-2">
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-200">
                Title <span className="text-red-500">*</span>
              </label>
              <Input
                value={createTaskForm.title}
                onChange={(event) =>
                  setCreateTaskForm((prev) => ({ ...prev, title: event.target.value }))
                }
                placeholder="Enter task title"
                disabled={isSavingTask}
                autoFocus
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-200">
                Description
              </label>
              <Textarea
                value={createTaskForm.description}
                onChange={(event) =>
                  setCreateTaskForm((prev) => ({ ...prev, description: event.target.value }))
                }
                placeholder="Describe the task"
                rows={4}
                disabled={isSavingTask}
              />
            </div>

            {(availableStatuses.length > 0 || availablePriorities.length > 0) && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {availableStatuses.length > 0 && (
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-700 dark:text-gray-200">
                      Status
                    </label>
                    <Select
                      value={createTaskForm.status || defaultStatusValue}
                      onValueChange={(value) =>
                        setCreateTaskForm((prev) => ({ ...prev, status: value }))
                      }
                      disabled={isSavingTask}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select status" />
                      </SelectTrigger>
                      <SelectContent>
                        {availableStatuses.map(({ value, label }) => (
                          <SelectItem key={value} value={value}>
                            {label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}

                {availablePriorities.length > 0 && (
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-700 dark:text-gray-200">
                      Priority
                    </label>
                    <Select
                      value={createTaskForm.priority || defaultPriorityValue}
                      onValueChange={(value) =>
                        setCreateTaskForm((prev) => ({ ...prev, priority: value }))
                      }
                      disabled={isSavingTask}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select priority" />
                      </SelectTrigger>
                      <SelectContent>
                        {availablePriorities.map(({ value, label }) => (
                          <SelectItem key={value} value={value}>
                            {label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </div>
            )}
          </div>
          <DialogFooter className="gap-2 sm:gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                if (isSavingTask) return;
                resetCreateTaskState();
              }}
              disabled={isSavingTask}
            >
              Cancel
            </Button>
            <Button
              type="button"
              onClick={handleConfirmCreateTask}
              disabled={isSavingTask || createTaskForm.title.trim().length === 0}
            >
              {isSavingTask ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating…
                </>
              ) : (
                "Create task"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <TaskDetailsModal
        task={selectedTask}
        open={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setSelectedTask(null);
        }}
        onUpdate={handleUpdateTask}
        projectId={projectIdForSprints}
      />
    </DndContext>
  );
}
