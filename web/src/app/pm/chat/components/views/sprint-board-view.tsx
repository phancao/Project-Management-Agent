// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragOverEvent,
  type DragStartEvent,
  type Modifier,
} from "@dnd-kit/core";
import { closestCorners } from "@dnd-kit/core";
import { useDroppable } from "@dnd-kit/core";
import { useSortable, SortableContext, verticalListSortingStrategy, horizontalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripHorizontal, GripVertical, Search, Settings2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "~/components/ui/button";
import { Card } from "~/components/ui/card";
import { Checkbox } from "~/components/ui/checkbox";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "~/components/ui/dialog";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";

import { useEpics } from "~/core/api/hooks/pm/use-epics";
import { usePriorities } from "~/core/api/hooks/pm/use-priorities";
import { useSprints } from "~/core/api/hooks/pm/use-sprints";
import { useStatuses } from "~/core/api/hooks/pm/use-statuses";
import { useTasks } from "~/core/api/hooks/pm/use-tasks";
import type { Task } from "~/core/api/hooks/pm/use-tasks";
import { resolveServiceURL } from "~/core/api/resolve-service-url";

import { usePMLoading } from "../../../context/pm-loading-context";
import { useProjectData } from "../../../hooks/use-project-data";
import { debug } from "../../../utils/debug";
import { traceSprintBoardEvent, isSprintBoardTraceEnabled } from "../../../utils/sprintboard-trace";

// Custom modifier to center the drag overlay on the cursor
const snapCenterToCursor: Modifier = ({ transform }) => {
  return {
    ...transform,
    x: transform.x - 0,
    y: transform.y - 20, // Offset to center vertically
  };
};

import {
  createOrderIdsFromStatusIds,
  detectDragType,
  extractTargetColumn,
  formatTaskUpdateError,
  getStatusIdFromOrderId,
  getStatusIdsFromOrderIds,
  getOrderId,
  isSameStatus,
  normalizeStatus,
  type DragInfo,
} from "./sprint-board-helpers";

import { TaskDetailsModal } from "../task-details-modal";

/* -------------------------------------------------------------------------------------------------
 * Helper Components
 * -----------------------------------------------------------------------------------------------*/

type DragMeasurements = {
  taskWidth: number | null;
  taskHeight: number | null;
  columnWidth: number | null;
  columnHeight: number | null;
};

type BoardTask = Task;

function TaskCard({ task, onClick, disabled }: { task: BoardTask; onClick: () => void; disabled?: boolean }) {
  const taskId = String(task.id);

  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: taskId,
    data: {
      type: "task",
      taskId,
      statusId: task.status,
    },
    disabled,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.3 : 1,
    zIndex: isDragging ? 5 : 1,
    pointerEvents: isDragging ? "none" : undefined,
  } as const;

  return (
    <div
      ref={setNodeRef}
      style={style}
      data-task-id={taskId}
      {...attributes}
      className="flex items-center gap-2 p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow transition cursor-pointer"
    >
      <div
        {...listeners}
        className="shrink-0 cursor-grab active:cursor-grabbing text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
        style={{ touchAction: "none" }}
      >
        <GripVertical className="w-4 h-4" />
      </div>
      <div className="flex-1 min-w-0" onClick={onClick}>
        <div className="font-medium text-sm text-gray-900 dark:text-gray-100 line-clamp-2 mb-1">{task.title}</div>
        <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-2">
          {task.priority && (
            <span className="px-2 py-0.5 rounded bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100">
              {task.priority}
            </span>
          )}
          {task.estimated_hours && <span>⏱️ {task.estimated_hours}h</span>}
        </div>
      </div>
    </div>
  );
}


function TaskDragPreview({ task, measurements }: { task: BoardTask | null; measurements: DragMeasurements }) {
  if (!task) return null;

  return (
    <div
      className="p-3 bg-white dark:bg-gray-800 rounded-lg border-2 border-blue-400 shadow-2xl opacity-95 cursor-grabbing"
      style={{
        width: measurements.taskWidth ? `${measurements.taskWidth}px` : 'auto',
        maxWidth: '24rem',
      }}
    >
      <div className="font-medium text-sm text-gray-900 dark:text-white line-clamp-2">
        {task.title}
      </div>
      {task.priority && (
        <span className="inline-block mt-1 px-2 py-0.5 text-xs font-medium rounded bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
          {task.priority}
        </span>
      )}
    </div>
  );
}

function ColumnDragPreview({ column, tasks, measurements }: { column: { id: string; title: string } | null; tasks: BoardTask[]; measurements: DragMeasurements }) {
  if (!column) return null;

  const previewTasks = tasks.slice(0, 3);

  return (
    <div
      className="pointer-events-none relative"
      style={{
        width: measurements.columnWidth ? `${measurements.columnWidth}px` : "20rem",
        height: measurements.columnHeight ? `${measurements.columnHeight}px` : undefined,
      }}
    >
      <div className="absolute top-0 left-0 right-0">
        <div className="rounded-xl shadow-2xl bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="flex items-center justify-between px-3 py-2 bg-gray-100 dark:bg-gray-800">
            <div className="flex items-center gap-2">
              <GripHorizontal className="w-4 h-4 text-gray-400" />
              <h3 className="font-semibold text-sm text-gray-800 dark:text-gray-100">{column.title}</h3>
            </div>
            <span className="text-xs text-gray-500 dark:text-gray-300">{tasks.length}</span>
          </div>
          <div className="p-3 space-y-2">
            {previewTasks.map((task) => (
              <div key={task.id} className="p-2 rounded bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-xs text-gray-700 dark:text-gray-300">
                {task.title}
              </div>
            ))}
            {tasks.length === 0 && <div className="text-xs text-gray-400">No tasks</div>}
            {tasks.length > 3 && (
              <div className="text-xs text-gray-500 dark:text-gray-400 text-center">
                +{tasks.length - 3} more
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

type SortableColumnProps = {
  column: { id: string; title: string };
  orderId: string;
  tasks: BoardTask[];
  onTaskClick: (task: Task) => void;
  draggedColumnId: string | null;
  hoveredColumnId: string | null;
};

function SortableColumn({ column, orderId, tasks, onTaskClick, draggedColumnId, hoveredColumnId }: SortableColumnProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: orderId,
    data: {
      type: "column",
      orderId,
      statusId: column.id,
    },
  });

  const { setNodeRef: setColumnDropRef } = useDroppable({
    id: `${orderId}-dropzone`,
    data: { type: "column-dropzone", orderId, statusId: column.id },
  });

  const columnStyle = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 5 : 1,
  } as const;

  const isActive = draggedColumnId === orderId;
  const isHovered = hoveredColumnId === column.id;

  return (
    <div ref={setNodeRef} style={columnStyle} data-order-id={orderId} className="w-[280px] sm:w-80 shrink-0">
      <div
        className={`flex items-center justify-between px-3 py-2 rounded-t-lg border-b ${isActive
            ? "bg-blue-100 dark:bg-blue-900 border-blue-400 dark:border-blue-500"
            : "bg-gray-100 dark:bg-gray-800 border-gray-200 dark:border-gray-700"
          }`}
      >
        <div className="flex items-center gap-2">
          <div
            {...listeners}
            {...attributes}
            className="cursor-grab active:cursor-grabbing text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            style={{ touchAction: "none" }}
          >
            <GripHorizontal className="w-4 h-4" />
          </div>
          <h3 className="font-semibold text-sm text-gray-800 dark:text-gray-100">{column.title}</h3>
        </div>
        <span className="text-xs text-gray-500 dark:text-gray-300">{tasks.length}</span>
      </div>
      <div
        ref={setColumnDropRef}
        className={`rounded-b-lg border-l border-r border-b ${isHovered
            ? "border-blue-400 dark:border-blue-500 bg-blue-50 dark:bg-blue-900/30 ring-2 ring-blue-400 dark:ring-blue-500"
            : isActive
              ? "border-blue-400 dark:border-blue-500 bg-blue-50 dark:bg-blue-900/30"
              : "border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900"
          } p-3 space-y-2 min-h-24 transition-all`}
      >
        <SortableContext items={tasks.map((task) => String(task.id))} strategy={verticalListSortingStrategy}>
          {tasks.length === 0 ? (
            <div className="text-sm text-gray-400">No tasks</div>
          ) : (
            tasks.map((task) => (
              <TaskCard key={task.id} task={task} onClick={() => onTaskClick(task)} />
            ))
          )}
        </SortableContext>
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------------------------------
 * Sprint Board View
 * -----------------------------------------------------------------------------------------------*/

export function SprintBoardView() {
  const { activeProjectId, projectIdForData: projectIdForTasks, activeProject } = useProjectData();
  const { state: loadingState, setTasksState } = usePMLoading();

  const previousProjectIdRef = useRef<string | null>(activeProjectId ?? null);
  const resetProjectIdRef = useRef<string | null>(activeProjectId ?? null);

  const [activeId, setActiveId] = useState<string | null>(null);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [isTaskModalOpen, setIsTaskModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [priorityFilter, setPriorityFilter] = useState<string>("all");
  const [epicFilter, setEpicFilter] = useState<string | null>(null);
  const [sprintFilter, setSprintFilter] = useState<string | null>(null);
  const [draggedColumnId, setDraggedColumnId] = useState<string | null>(null);
  const [hoveredColumnId, setHoveredColumnId] = useState<string | null>(null);

  const [columnOrderIds, setColumnOrderIds] = useState<string[]>([]);
  const [orderIdToStatusIdMap, setOrderIdToStatusIdMap] = useState<Map<string, string>>(new Map());
  const [columnOrder, setColumnOrder] = useState<string[]>([]);
  const [visibleColumns, setVisibleColumns] = useState<Set<string>>(new Set());
  const [isColumnDialogOpen, setIsColumnDialogOpen] = useState(false);

  useEffect(() => {
    const currentProjectId = activeProjectId ?? null;
    const previousProjectId = resetProjectIdRef.current;

    if (currentProjectId !== previousProjectId) {
      debug.project("SprintBoardView project change detected: resetting board state", {
        previousProjectId,
        currentProjectId,
      });

      setColumnOrderIds([]);
      setColumnOrder([]);
      setOrderIdToStatusIdMap(new Map<string, string>());
      setVisibleColumns(new Set<string>());
      setDraggedColumnId(null);
      setActiveId(null);
    }

    resetProjectIdRef.current = currentProjectId;
  }, [activeProjectId]);

  const [dragMeasurements, setDragMeasurements] = useState<DragMeasurements>({
    taskWidth: null,
    taskHeight: null,
    columnWidth: null,
    columnHeight: null,
  });

  const { tasks, loading, error, refresh: refreshTasks } = useTasks(projectIdForTasks ?? undefined);
  const { priorities: backendPriorities } = usePriorities(activeProjectId ?? undefined);
  const { epics } = useEpics(activeProjectId ?? undefined);
  // Use projectIdForTasks for sprints to match tasks (ensures same cache key)
  const { sprints } = useSprints(projectIdForTasks ?? "");
  const {
    statuses: availableStatuses,
    loading: statusesLoading,
    error: statusesError,
    refresh: refreshStatuses,
  } = useStatuses(activeProjectId ?? undefined, "task");

  useEffect(() => {
    const projectId = activeProjectId ?? null;
    const boardSnapshot = {
      projectId,
      previousProjectId: previousProjectIdRef.current,
      columnOrderIds,
      columnOrder,
      orderIdToStatusId: Array.from(orderIdToStatusIdMap.entries()),
      availableStatuses: (availableStatuses ?? []).map((status) => ({ id: String(status.id), name: status.name })),
      visibleColumns: Array.from(visibleColumns).map(String),
    };

    debug.project("SprintBoardView project effect: mount", boardSnapshot);

    previousProjectIdRef.current = projectId;

    return () => {
      debug.project("SprintBoardView project effect: cleanup", boardSnapshot);
    };
  }, [activeProjectId, columnOrderIds, columnOrder, orderIdToStatusIdMap, availableStatuses, visibleColumns]);

  // Only require canLoadTasks if we don't have cached tasks
  // This allows cached data to display immediately even if canLoadTasks is false
  const shouldLoadTasks = loadingState.canLoadTasks && activeProjectId;
  const hasCachedTasks = tasks.length > 0 && !loading;

  const availablePriorities = useMemo(() => {
    if (backendPriorities && backendPriorities.length > 0) {
      return backendPriorities.map((priority) => ({ value: priority.name.toLowerCase(), label: priority.name }));
    }
    const seen = new Map<string, string>();
    tasks.forEach((task) => {
      if (task.priority) {
        const lower = task.priority.toLowerCase();
        if (!seen.has(lower)) seen.set(lower, task.priority);
      }
    });
    return Array.from(seen.entries()).map(([value, label]) => ({ value, label }));
  }, [backendPriorities, tasks]);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    })
  );

  const [isLoadingFromStorage, setIsLoadingFromStorage] = useState(false);
  const [lastLoadedProjectId, setLastLoadedProjectId] = useState<string | null>(null);
  const datasetDebugKeyRef = useRef<string | null>(null);
  const logTaskDragEvent = useCallback(
    (event: string, payload: Record<string, unknown>) => {
      if (!isSprintBoardTraceEnabled()) return;
      traceSprintBoardEvent(event, payload);
    },
    []
  );

  const getStorageKey = useCallback((projectId: string | null) => {
    if (!projectId) return null;
    return `sprint-board-column-order-${projectId}`;
  }, []);

  const getVisibilityStorageKey = useCallback((projectId: string | null) => {
    if (!projectId) return null;
    return `sprint-board-column-visibility-${projectId}`;
  }, []);

  const loadColumnOrderFromStorage = useCallback(
    (projectId: string | null): string[] | null => {
      if (typeof window === "undefined" || !projectId) return null;
      const key = getStorageKey(projectId);
      if (!key) return null;
      try {
        const saved = localStorage.getItem(key);
        if (saved) {
          const parsed = JSON.parse(saved);
          if (Array.isArray(parsed) && parsed.length > 0) return parsed;
        }
      } catch (err) {
        debug.error("Failed to load column order from localStorage", err);
      }
      return null;
    },
    [getStorageKey]
  );

  const saveColumnOrderToStorage = useCallback(
    (projectId: string | null, order: string[]) => {
      if (typeof window === "undefined" || !projectId || order.length === 0) return;
      const key = getStorageKey(projectId);
      if (!key) return;
      try {
        localStorage.setItem(key, JSON.stringify(order));
      } catch (err) {
        debug.error("Failed to save column order", err);
      }
    },
    [getStorageKey]
  );

  const resetColumnOrderToDefault = useCallback(
    (projectId: string | null, statuses: typeof availableStatuses) => {
      if (!statuses || statuses.length === 0) return;
      const sorted = [...statuses].sort((a, b) => String(a.id).localeCompare(String(b.id)));
      const defaultOrder = sorted.map((status) => String(status.id));
      if (projectId && typeof window !== "undefined") {
        const key = getStorageKey(projectId);
        if (key) localStorage.removeItem(key);
      }
      setColumnOrder(defaultOrder);
    },
    [getStorageKey]
  );

  useEffect(() => {
    if (availableStatuses && availableStatuses.length > 0 && activeProjectId) {
      if (lastLoadedProjectId !== activeProjectId) {
        setIsLoadingFromStorage(true);
        const savedOrder = loadColumnOrderFromStorage(activeProjectId);

        if (savedOrder && savedOrder.length > 0) {
          const validStatusIds = new Set(availableStatuses.map((status) => String(status.id)));
          const validOrder = savedOrder.filter((id) => validStatusIds.has(String(id)));
          const missingStatuses = availableStatuses
            .filter((status) => !validOrder.includes(String(status.id)))
            .sort((a, b) => String(a.id).localeCompare(String(b.id)));
          const finalOrder = [...validOrder, ...missingStatuses.map((status) => String(status.id))];
          const { orderIds, mapping } = createOrderIdsFromStatusIds(finalOrder);
          setColumnOrderIds(orderIds);
          setOrderIdToStatusIdMap(mapping);
          setColumnOrder(finalOrder);
        } else {
          const sortedStatuses = [...availableStatuses].sort((a, b) => String(a.id).localeCompare(String(b.id)));
          const defaultOrder = sortedStatuses.map((status) => String(status.id));
          const { orderIds, mapping } = createOrderIdsFromStatusIds(defaultOrder);
          setColumnOrderIds(orderIds);
          setOrderIdToStatusIdMap(mapping);
          setColumnOrder(defaultOrder);
        }

        const visibilityKey = getVisibilityStorageKey(activeProjectId);
        if (visibilityKey) {
          try {
            const savedVisibility = localStorage.getItem(visibilityKey);
            if (savedVisibility) {
              const parsed = JSON.parse(savedVisibility);
              if (Array.isArray(parsed)) setVisibleColumns(new Set(parsed.map(String)));
            }
          } catch (err) {
            debug.error("Failed to load column visibility", err);
          }
        }

        setLastLoadedProjectId(activeProjectId);
        setTimeout(() => setIsLoadingFromStorage(false), 100);
      }
    } else if (!activeProjectId && lastLoadedProjectId) {
      setColumnOrder([]);
      setColumnOrderIds([]);
      setOrderIdToStatusIdMap(new Map());
      setVisibleColumns(new Set());
      setLastLoadedProjectId(null);
    }
  }, [availableStatuses, activeProjectId, lastLoadedProjectId, getVisibilityStorageKey, loadColumnOrderFromStorage]);

  useEffect(() => {
    if (availableStatuses && availableStatuses.length > 0 && activeProjectId) {
      const resetFlag = typeof window !== "undefined" ? localStorage.getItem("sprint-board-reset-column-order") : null;
      if (resetFlag === "true") {
        resetColumnOrderToDefault(activeProjectId, availableStatuses);
        localStorage.removeItem("sprint-board-reset-column-order");
      }
    }
  }, [availableStatuses, activeProjectId, resetColumnOrderToDefault]);

  useEffect(() => {
    if (isLoadingFromStorage) return;
    if (!activeProjectId || !availableStatuses) return;
    if (columnOrderIds.length === 0) return;

    const statusOrder = getStatusIdsFromOrderIds(columnOrderIds, orderIdToStatusIdMap);
    if (statusOrder.length > 0) {
      saveColumnOrderToStorage(activeProjectId, statusOrder);
      setColumnOrder(statusOrder);
    }
  }, [columnOrderIds, activeProjectId, availableStatuses, orderIdToStatusIdMap, saveColumnOrderToStorage, isLoadingFromStorage]);

  useEffect(() => {
    if (isLoadingFromStorage) return;
    if (!activeProjectId || !availableStatuses) return;
    const key = getVisibilityStorageKey(activeProjectId);
    if (!key) return;
    if (visibleColumns.size === 0) return;
    try {
      localStorage.setItem(key, JSON.stringify(Array.from(visibleColumns)));
    } catch (err) {
      debug.error("Failed to save column visibility", err);
    }
  }, [visibleColumns, activeProjectId, availableStatuses, getVisibilityStorageKey, isLoadingFromStorage]);

  useEffect(() => {
    if (!availableStatuses || availableStatuses.length === 0) return;

    const mappedStatusIds = new Set(
      Array.from(orderIdToStatusIdMap.values()).map((value) => String(value))
    );
    const missingStatuses = availableStatuses.filter(
      (status) => !mappedStatusIds.has(String(status.id))
    );

    if (missingStatuses.length === 0) return;

    const nextMap = new Map(orderIdToStatusIdMap);
    const nextOrderIds = [...columnOrderIds];
    const nextColumnOrder = [...columnOrder];

    missingStatuses.forEach((status) => {
      const statusId = String(status.id);
      const newOrderId = getOrderId(nextMap.size);
      nextMap.set(newOrderId, statusId);
      nextOrderIds.push(newOrderId);
      nextColumnOrder.push(statusId);
    });

    setOrderIdToStatusIdMap(nextMap);
    setColumnOrderIds(nextOrderIds);
    setColumnOrder(nextColumnOrder);
  }, [availableStatuses, orderIdToStatusIdMap, columnOrderIds, columnOrder]);

  useEffect(() => {
    if (!availableStatuses || availableStatuses.length === 0) return;

    const statusIds = new Set(availableStatuses.map((status) => String(status.id)));
    const mappedStatusIds = new Set(Array.from(orderIdToStatusIdMap.values()).map((value) => String(value)));

    const missingStatusIds = Array.from(statusIds).filter((id) => !mappedStatusIds.has(id));
    const extraStatusIds = Array.from(mappedStatusIds).filter((id) => !statusIds.has(id));
    const hasOrderIds = columnOrderIds.length > 0;

    if (missingStatusIds.length > 0 || extraStatusIds.length > 0 || !hasOrderIds) {
      if (isSprintBoardTraceEnabled()) {
        traceSprintBoardEvent("debug:column-order-reset", {
          projectId: activeProjectId,
          projectName: activeProject?.name ?? null,
          provider: (activeProject as any)?.provider ?? null,
          reason: {
            missingStatusIds,
            extraStatusIds,
            hasOrderIds,
          },
          currentOrderIds: columnOrderIds,
          currentMapping: Array.from(orderIdToStatusIdMap.entries()),
        });
      }

      resetColumnOrderToDefault(activeProjectId ?? null, availableStatuses);
    }
  }, [availableStatuses, orderIdToStatusIdMap, columnOrderIds, activeProjectId, activeProject, resetColumnOrderToDefault]);

  useEffect(() => {
    if (!availableStatuses || availableStatuses.length === 0) return;

    const statuses = availableStatuses;

    const statusIds = statuses.map((status) => String(status.id));
    const statusIdSet = new Set(statusIds);
    const mappedStatusIds = Array.from(orderIdToStatusIdMap.values()).map((value) => String(value));

    const missingStatus = statusIds.some((id) => !mappedStatusIds.includes(id));
    const extraStatus = mappedStatusIds.some((id) => !statusIdSet.has(id));
    const hasOrderIds = columnOrderIds.length > 0;

    if (missingStatus || extraStatus || !hasOrderIds) {
      if (isSprintBoardTraceEnabled()) {
        traceSprintBoardEvent("debug:column-order-reset", {
          projectId: activeProjectId,
          reason: {
            missingStatus,
            extraStatus,
            hasOrderIds,
          },
          statuses: statusIds,
          mappedStatusIds,
          columnOrderIds,
        });
      }
      resetColumnOrderToDefault(activeProjectId ?? null, statuses);
    }
  }, [availableStatuses, orderIdToStatusIdMap, columnOrderIds, activeProjectId, resetColumnOrderToDefault]);

  const filteredTasks = useMemo(() => {
    if (loading && (!tasks || tasks.length === 0)) return [];
    if (!tasks || tasks.length === 0) return [];

    let result = [...tasks];
    if (searchQuery.trim()) {
      const query = searchQuery.trim().toLowerCase();
      result = result.filter((task) => (task.title ?? "").toLowerCase().includes(query));
    }
    if (priorityFilter !== "all") {
      result = result.filter((task) => (task.priority ?? "").toLowerCase() === priorityFilter);
    }
    if (epicFilter && epicFilter !== "all") {
      if (epicFilter === "none") result = result.filter((task) => !task.epic_id);
      else result = result.filter((task) => task.epic_id === epicFilter);
    }
    if (sprintFilter && sprintFilter !== "all") {
      if (sprintFilter === "none") result = result.filter((task) => !task.sprint_id);
      else result = result.filter((task) => task.sprint_id === sprintFilter);
    }
    return result;
  }, [tasks, loading, searchQuery, priorityFilter, epicFilter, sprintFilter]);

  const getTasksForColumn = useCallback(
    (statusId: string): BoardTask[] => {
      if (!availableStatuses) return [];
      const status = availableStatuses.find((s) => String(s.id) === String(statusId));
      if (!status) return [];

      const normalizedStatus = normalizeStatus(status.name);
      const baseTasks = filteredTasks
        .filter((task) => {
          const taskStatus = normalizeStatus(task.status);
          if (!taskStatus && status.is_default) return true;
          return taskStatus === normalizedStatus;
        })
        .map((task) => task) as BoardTask[];

      return baseTasks;
    },
    [availableStatuses, filteredTasks]
  );

  const orderedColumns = useMemo(() => {
    if (!availableStatuses) return [];

    let columnsToRender = availableStatuses;
    if (visibleColumns.size > 0) {
      columnsToRender = availableStatuses.filter((status) => visibleColumns.has(String(status.id)));
    }

    const statusIdToColumn = new Map<string, { id: string; title: string; tasks: BoardTask[] }>();
    columnsToRender.forEach((status) => {
      statusIdToColumn.set(String(status.id), {
        id: String(status.id),
        title: status.name,
        tasks: getTasksForColumn(String(status.id)),
      });
    });

    const ordered: { id: string; title: string; orderId: string; tasks: BoardTask[] }[] = [];

    columnOrderIds.forEach((orderId) => {
      const statusId = getStatusIdFromOrderId(orderId, orderIdToStatusIdMap);
      if (!statusId) return;
      const column = statusIdToColumn.get(String(statusId));
      if (!column) return;
      ordered.push({ ...column, orderId });
      statusIdToColumn.delete(String(statusId));
    });

    statusIdToColumn.forEach((column, statusId) => {
      ordered.push({ ...column, orderId: statusId });
    });

    return ordered;
  }, [availableStatuses, columnOrderIds, orderIdToStatusIdMap, visibleColumns, getTasksForColumn]);

  const activeColumnOverlay = useMemo(() => {
    if (!draggedColumnId) return null;
    return orderedColumns.find((column) => column.orderId === draggedColumnId) ?? null;
  }, [draggedColumnId, orderedColumns]);

  useEffect(() => {
    if (!isSprintBoardTraceEnabled()) return;
    if (!activeProjectId) return;

    traceSprintBoardEvent("debug:column-render", {
      projectId: activeProjectId,
      projectName: activeProject?.name ?? null,
      provider: (activeProject as any)?.provider ?? null,
      columnCount: orderedColumns.length,
      columnOrderIds,
      visibleColumns: Array.from(visibleColumns),
      mappedStatusIds: Array.from(orderIdToStatusIdMap.entries()),
      columns: orderedColumns.map((column) => ({
        orderId: column.orderId,
        statusId: column.id,
        title: column.title,
        taskCount: column.tasks.length,
      })),
    });
  }, [
    orderedColumns,
    columnOrderIds,
    visibleColumns,
    orderIdToStatusIdMap,
    activeProjectId,
    activeProject,
  ]);

  useEffect(() => {
    if (!isSprintBoardTraceEnabled()) return;
    if (!activeProjectId) return;
    if (loading || statusesLoading) return;
    const statuses = availableStatuses ?? [];
    if (statuses.length === 0) return;

    const snapshotKey = `${activeProjectId}:${tasks.length}:${statuses.length}`;
    if (datasetDebugKeyRef.current === snapshotKey) return;
    datasetDebugKeyRef.current = snapshotKey;

    const statusBuckets = statuses.map((status) => ({
      statusId: String(status.id),
      statusName: status.name,
      normalizedKey: normalizeStatus(status.name),
      isDefault: Boolean(status.is_default),
      taskIds: [] as string[],
    }));

    const normalizedIndex = new Map<string, number[]>();
    statusBuckets.forEach((bucket, index) => {
      const key = bucket.normalizedKey;
      const existing = normalizedIndex.get(key);
      if (existing) {
        existing.push(index);
      } else {
        normalizedIndex.set(key, [index]);
      }
    });

    const defaultIndex = statusBuckets.findIndex((bucket) => bucket.isDefault);
    const unmatchedTasks: { id: string; status: string | null | undefined }[] = [];

    tasks.forEach((task) => {
      const normalizedTaskStatus = normalizeStatus(task.status);
      let targetIndex: number | undefined;

      const matchingIndices = normalizedIndex.get(normalizedTaskStatus);
      if (matchingIndices && matchingIndices.length > 0) {
        targetIndex = matchingIndices[0];
      } else if (!normalizedTaskStatus && defaultIndex >= 0) {
        targetIndex = defaultIndex;
      }

      if (targetIndex !== undefined) {
        const targetBucket = statusBuckets[targetIndex];
        if (targetBucket) {
          targetBucket.taskIds.push(String(task.id));
        } else {
          unmatchedTasks.push({ id: String(task.id), status: task.status });
        }
      } else {
        unmatchedTasks.push({ id: String(task.id), status: task.status });
      }
    });

    const statusSummary = statusBuckets.map((bucket) => ({
      statusId: bucket.statusId,
      statusName: bucket.statusName,
      isDefault: bucket.isDefault,
      taskCount: bucket.taskIds.length,
      sampleTaskIds: bucket.taskIds.slice(0, 5),
    }));

    traceSprintBoardEvent("debug:task-status-distribution", {
      projectId: activeProjectId,
      projectName: activeProject?.name ?? null,
      provider: (activeProject as any)?.provider ?? null,
      tasksCount: tasks.length,
      statusesCount: statuses.length,
      statusSummary,
      unmatchedCount: unmatchedTasks.length,
      unmatchedSample: unmatchedTasks.slice(0, 10),
    });
  }, [
    activeProjectId,
    activeProject,
    tasks,
    availableStatuses,
    loading,
    statusesLoading,
  ]);

  const taskIdsSet = useMemo(() => new Set(tasks.map((task) => String(task.id))), [tasks]);

  const handleDragStart = useCallback(
    (event: DragStartEvent) => {
      const info = detectDragType(event, columnOrderIds, taskIdsSet);
      setActiveId(info.id);

      if (info.type === "column" && info.orderId) {
        setDraggedColumnId(info.orderId);

        try {
          const columnEl = document.querySelector(`[data-order-id="${info.orderId}"]`);
          if (columnEl instanceof HTMLElement) {
            const rect = columnEl.getBoundingClientRect();
            setDragMeasurements((prev) => ({ ...prev, columnWidth: rect.width, columnHeight: rect.height }));
            if (isSprintBoardTraceEnabled()) {
              const column = orderedColumns.find((entry) => entry.orderId === info.orderId);
              traceSprintBoardEvent("debug:column-measurement", {
                projectId: activeProjectId,
                projectName: activeProject?.name ?? null,
                provider: (activeProject as any)?.provider ?? null,
                orderId: info.orderId,
                statusId: column?.id ?? null,
                title: column?.title ?? null,
                taskCount: column?.tasks.length ?? null,
                width: rect.width,
                height: rect.height,
              });
            }
          }
        } catch (err) {
          debug.warn("Failed to measure column", err);
        }
      } else if (info.type === "task") {
        setDraggedColumnId(null);
        try {
          const taskEl = document.querySelector(`[data-task-id="${info.id}"]`);
          if (taskEl instanceof HTMLElement) {
            const rect = taskEl.getBoundingClientRect();
            setDragMeasurements((prev) => ({ ...prev, taskWidth: rect.width, taskHeight: rect.height }));
          }
        } catch (err) {
          debug.warn("Failed to measure task", err);
        }
      }
    },
    [
      columnOrderIds,
      taskIdsSet,
      orderedColumns,
      activeProjectId,
      activeProject,
    ]
  );

  const handleDragOver = useCallback(
    (event: DragOverEvent) => {
      const { over, active } = event;

      // Track which column is being hovered for visual feedback
      if (over && active) {
        const dragInfo = detectDragType(event, columnOrderIds, taskIdsSet);

        if (dragInfo.type === "task") {
          // Extract the target column from the over element
          const extraction = extractTargetColumn(
            String(over.id),
            over.data.current,
            columnOrderIds,
            orderIdToStatusIdMap,
            availableStatuses ?? [],
            tasks
          );

          if (extraction.statusId) {
            setHoveredColumnId(String(extraction.statusId));
          } else {
            setHoveredColumnId(null);
          }
        } else {
          setHoveredColumnId(null);
        }
      } else {
        setHoveredColumnId(null);
      }
    },
    [columnOrderIds, taskIdsSet, orderIdToStatusIdMap, availableStatuses, tasks]
  );

  const applyColumnReorder = useCallback(
    (activeOrderId: string, overOrderId: string, position: "top" | "bottom" | undefined) => {
      if (activeOrderId === overOrderId) return;
      const withoutActive = columnOrderIds.filter((id) => id !== activeOrderId);

      let insertIndex = withoutActive.indexOf(overOrderId);
      if (insertIndex === -1) {
        const nextOrder = [...withoutActive, activeOrderId];
        if (!arrayEqual(nextOrder, columnOrderIds)) {
          setColumnOrderIds(nextOrder);
          const statusIds = getStatusIdsFromOrderIds(nextOrder, orderIdToStatusIdMap);
          setColumnOrder(statusIds);
          if (activeProjectId && statusIds.length > 0) {
            saveColumnOrderToStorage(activeProjectId, statusIds);
          }
        }
        return;
      }

      if (position === "bottom") insertIndex += 1;
      if (position === undefined) {
        const originalIndex = columnOrderIds.indexOf(activeOrderId);
        const overIndex = columnOrderIds.indexOf(overOrderId);
        if (originalIndex < overIndex) insertIndex = Math.min(insertIndex + 1, withoutActive.length);
      }

      const nextOrder = [
        ...withoutActive.slice(0, insertIndex),
        activeOrderId,
        ...withoutActive.slice(insertIndex),
      ];

      if (!arrayEqual(nextOrder, columnOrderIds)) {
        setColumnOrderIds(nextOrder);
        const statusIds = getStatusIdsFromOrderIds(nextOrder, orderIdToStatusIdMap);
        setColumnOrder(statusIds);
        if (activeProjectId && statusIds.length > 0) {
          saveColumnOrderToStorage(activeProjectId, statusIds);
        }

      }
    },
    [columnOrderIds, orderIdToStatusIdMap, activeProjectId, saveColumnOrderToStorage]
  );

  const handleUpdateTask = useCallback(
    async (taskId: string, updates: Partial<Task>): Promise<Task> => {
      if (!activeProjectId) {
        const error = new Error("Project ID is required to update a task");
        return Promise.reject(error);
      }

      const url = new URL(resolveServiceURL(`pm/tasks/${taskId}`));
      url.searchParams.set("project_id", activeProjectId);

      const response = await fetch(url.toString(), {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      });

      if (!response.ok) {
        const errorText = await response.text();
        let message = `Failed to update task: ${response.status} ${response.statusText}`;
        try {
          const data = JSON.parse(errorText);
          message = data.detail || data.message || data.error || message;
        } catch {
          if (errorText) message = errorText;
        }
        const error = new Error(message);
        (error as any).isHandled = true;
        return Promise.reject(error);
      }

      const result = (await response.json()) as Task;

      setSelectedTask((prev) => {
        if (!prev || prev.id !== result.id) return prev;
        return { ...prev, ...result };
      });

      if (refreshTasks) {
        refreshTasks();
      } else if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("pm_refresh", { detail: { type: "pm_refresh" } }));
      }

      return result;
    },
    [activeProjectId, refreshTasks]
  );

  const handleUpdateTaskForModal = useCallback(
    (taskId: string, updates: Partial<Task>) => handleUpdateTask(taskId, updates).then(() => undefined),
    [handleUpdateTask]
  );

  const finishTaskDrag = useCallback(
    async (dragInfo: DragInfo, event: DragEndEvent) => {
      const { over } = event;
      setActiveId(null);
      setHoveredColumnId(null);

      if (!over || dragInfo.type !== "task") {
        logTaskDragEvent("task-drag:ignored", {
          projectId: activeProjectId,
          reason: !over ? "no-over" : "not-task",
          dragType: dragInfo.type,
        });
        return;
      }
      const overId = String(over.id);

      const extraction = extractTargetColumn(
        overId,
        over.data.current,
        columnOrderIds,
        orderIdToStatusIdMap,
        availableStatuses ?? [],
        tasks,
        (stage, details) => {
          logTaskDragEvent('task-drag:extract-debug', {
            projectId: activeProjectId,
            stage,
            ...details,
          });
        }
      );
      const targetColumnId = extraction.statusId;
      const targetOrderId = extraction.orderId;

      if (!targetColumnId || !availableStatuses) {
        logTaskDragEvent("task-drag:ignored", {
          projectId: activeProjectId,
          taskId: dragInfo.id,
          reason: !targetColumnId ? "no-target-column" : "no-statuses",
          overId,
          availableStatusesCount: availableStatuses?.length ?? 0,
          columnOrderIds,
          orderMapping: Array.from(orderIdToStatusIdMap.entries()),
          extraction,
        });
        return;
      }

      const task = tasks.find((t) => String(t.id) === dragInfo.id);
      if (!task) {
        logTaskDragEvent("task-drag:ignored", {
          projectId: activeProjectId,
          reason: "task-not-found",
          taskId: dragInfo.id,
        });
        return;
      }

      const targetStatus = availableStatuses.find((status) => String(status.id) === String(targetColumnId));
      if (!targetStatus) {
        logTaskDragEvent("task-drag:ignored", {
          projectId: activeProjectId,
          reason: "target-status-not-found",
          taskId: dragInfo.id,
          targetColumnId,
          availableStatuses: availableStatuses.map((status) => ({ id: String(status.id), name: status.name })),
        });
        return;
      }

      const newStatus = targetStatus.name;
      if (!newStatus || isSameStatus(newStatus, task.status)) {
        logTaskDragEvent("task-drag:ignored", {
          projectId: activeProjectId,
          reason: !newStatus ? "empty-status" : "status-unchanged",
          taskId: dragInfo.id,
          currentStatus: task.status,
          targetStatusName: newStatus,
        });
        return;
      }

      const targetStatusExists = availableStatuses.some((status) => String(status.id) === String(targetColumnId));
      if (!targetStatusExists) {
        logTaskDragEvent("task-drag:ignored", {
          projectId: activeProjectId,
          reason: "target-status-not-in-list",
          taskId: dragInfo.id,
          targetColumnId,
          targetOrderId,
        });
        return;
      }

      // Use status name for the API call (OpenProject will resolve it)
      const statusValue = newStatus;

      try {
        if (!dragInfo.id || dragInfo.id === "undefined" || dragInfo.id === "null") {
          toast.error("Invalid task", { description: "Cannot update task: invalid task ID." });
          logTaskDragEvent("task-drag:error", {
            projectId: activeProjectId,
            reason: "invalid-task-id",
            taskId: dragInfo.id,
          });
          return;
        }

        logTaskDragEvent("task-drag:update", {
          projectId: activeProjectId,
          taskId: dragInfo.id,
          fromStatus: task.status,
          toStatus: newStatus,
          targetStatusId: targetStatus.id,
        });

        const result = await handleUpdateTask(dragInfo.id, { status: statusValue });
        if (!result) {
          toast.error("Update failed", { description: "The task update did not return a result." });
          logTaskDragEvent("task-drag:update", {
            projectId: activeProjectId,
            taskId: dragInfo.id,
            outcome: "no-result",
          });
          return;
        }

        const actualStatus = normalizeStatus(result.status);
        const expectedStatus = normalizeStatus(newStatus);
        const originalStatus = normalizeStatus(task.status);

        if (actualStatus === originalStatus) {
          toast.error("Status update failed", {
            description: `The task status remains "${task.status}". This may be due to workflow restrictions or permissions.`,
          });
          logTaskDragEvent("task-drag:update", {
            projectId: activeProjectId,
            taskId: dragInfo.id,
            outcome: "status-unchanged",
            serverStatus: result.status,
            originalStatus: task.status,
          });
          return;
        }

        if (actualStatus !== expectedStatus) {
          toast.error("Status update partially successful", {
            description: `Task status changed to "${result.status}" instead of "${newStatus}". Workflow rules may apply.`,
          });
          logTaskDragEvent("task-drag:update", {
            projectId: activeProjectId,
            taskId: dragInfo.id,
            outcome: "status-mismatch",
            serverStatus: result.status,
            expectedStatus: newStatus,
          });
          return;
        }

        toast.success("Task status updated", {
          description: `Task moved to "${newStatus}"`,
        });
        logTaskDragEvent("task-drag:update", {
          projectId: activeProjectId,
          taskId: dragInfo.id,
          outcome: "success",
          serverStatus: result.status,
        });
      } catch (err) {
        const { message, description } = formatTaskUpdateError(err);
        toast.error(message, { description });
        logTaskDragEvent("task-drag:update", {
          projectId: activeProjectId,
          taskId: dragInfo.id,
          outcome: "error",
          error: err instanceof Error ? err.message : String(err),
        });
      }
    },
    [availableStatuses, columnOrderIds, orderIdToStatusIdMap, tasks, handleUpdateTask, activeProjectId, logTaskDragEvent]
  );

  const handleDragEnd = useCallback(
    async (event: DragEndEvent) => {
      const dragInfo = detectDragType(event, columnOrderIds, taskIdsSet);

      if (dragInfo.type === "column" && dragInfo.orderId) {
        const { over } = event;
        setDraggedColumnId(null);
        setActiveId(null);
        setHoveredColumnId(null);

        if (!over) return;

        const overData = over.data?.current;
        const overId = String(over.id);
        const { orderId: overOrderId } = extractTargetColumn(
          overId,
          overData,
          columnOrderIds,
          orderIdToStatusIdMap,
          availableStatuses ?? [],
          tasks
        );

        if (!overOrderId) return;

        applyColumnReorder(dragInfo.orderId, overOrderId, overData?.position as "top" | "bottom" | undefined);
        return;
      }

      if (dragInfo.type === "task") {
        await finishTaskDrag(dragInfo, event);
      }
    },
    [columnOrderIds, taskIdsSet, applyColumnReorder, finishTaskDrag, availableStatuses, orderIdToStatusIdMap, tasks]
  );

  useEffect(() => {
    if (selectedTask) setIsTaskModalOpen(true);
  }, [selectedTask]);

  const handleTaskClick = (task: Task) => {
    setSelectedTask(task);
  };

  const sensorsContext = useMemo(() => sensors, [sensors]);

  const hasTasks = tasks.length > 0;
  // Only show loading if:
  // 1. Filter data is loading AND we don't have cached tasks, OR
  // 2. We should load tasks AND we're actually loading AND we don't have tasks yet
  // This ensures cached data (hasTasks=true, loading=false) displays immediately
  // If we have cached tasks, show them even if filter data is still loading
  const isLoadingBoard = (loadingState.filterData.loading && !hasTasks) || (shouldLoadTasks && loading && !hasTasks);

  if (isLoadingBoard) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-gray-500 dark:text-gray-400">Loading board...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20 px-4">
        <div className="text-red-500 font-semibold mb-2">Error loading tasks</div>
        <div className="text-red-400 text-sm text-center max-w-2xl">{error.message}</div>
        <div className="mt-4 text-xs text-muted-foreground">Check your project configuration and try again.</div>
      </div>
    );
  }

  if (statusesError) {
    return (
      <div className="flex flex-col items-center justify-center py-20 px-4">
        <div className="text-red-500 font-semibold mb-2">Error loading statuses</div>
        <div className="text-red-400 text-sm text-center max-w-2xl">{statusesError.message}</div>
        <Button className="mt-4" variant="outline" onClick={() => refreshStatuses()}>
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-4">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Sprint Board</h2>
          {availableStatuses.length > 0 && (
            <Button variant="outline" size="sm" onClick={() => setIsColumnDialogOpen(true)} className="gap-2">
              <Settings2 className="w-4 h-4" />
              Columns
            </Button>
          )}
        </div>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          {filteredTasks.length} of {tasks.length} tasks
        </div>
      </div>

      <Card className="p-4 mb-4">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4" />
            <Input
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              className="pl-10"
              placeholder="Search tasks..."
            />
          </div>
          <div className="flex gap-3">
            {availablePriorities.length > 0 && (
              <Select value={priorityFilter} onValueChange={setPriorityFilter}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="Priority" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Priority</SelectItem>
                  {availablePriorities.map((priority) => (
                    <SelectItem key={priority.value} value={priority.value}>
                      {priority.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
            {epics.length > 0 && (
              <Select value={epicFilter ?? "all"} onValueChange={(value) => setEpicFilter(value === "all" ? null : value)}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="Epic" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Epics</SelectItem>
                  <SelectItem value="none">No Epic</SelectItem>
                  {epics.map((epic) => (
                    <SelectItem key={epic.id} value={epic.id}>
                      {epic.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
            {sprints.length > 0 && (
              <Select value={sprintFilter ?? "all"} onValueChange={(value) => setSprintFilter(value === "all" ? null : value)}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="Sprint" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Sprints</SelectItem>
                  <SelectItem value="none">No Sprint</SelectItem>
                  {sprints.map((sprint) => (
                    <SelectItem key={sprint.id} value={sprint.id}>
                      {sprint.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>
        </div>
      </Card>

      <Dialog open={isColumnDialogOpen} onOpenChange={setIsColumnDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Manage Columns</DialogTitle>
            <DialogDescription>Select which columns are visible on the board.</DialogDescription>
          </DialogHeader>
          <div className="space-y-2 max-h-[60vh] overflow-y-auto py-2">
            {availableStatuses.length === 0 ? (
              <div className="text-sm text-gray-500">No statuses available</div>
            ) : (
              availableStatuses.map((status) => {
                const statusId = String(status.id);
                const isVisible = visibleColumns.size === 0 || visibleColumns.has(statusId);
                const visibleCount = visibleColumns.size === 0 ? availableStatuses.length : visibleColumns.size;
                const isLastVisible = isVisible && visibleCount === 1;
                return (
                  <div key={statusId} className="flex items-center gap-3 px-2 py-1 rounded hover:bg-gray-50 dark:hover:bg-gray-800">
                    <Checkbox
                      id={`column-${statusId}`}
                      checked={isVisible}
                      disabled={isLastVisible}
                      onCheckedChange={(checked) => {
                        const current = visibleColumns.size === 0 ? new Set(availableStatuses.map((s) => String(s.id))) : new Set(visibleColumns);
                        if (checked) current.add(statusId);
                        else if (current.size > 1) current.delete(statusId);
                        setVisibleColumns(current);
                      }}
                    />
                    <Label className={`flex-1 cursor-pointer ${isLastVisible ? "opacity-50" : ""}`} htmlFor={`column-${statusId}`}>
                      {status.name}
                    </Label>
                  </div>
                );
              })
            )}
          </div>
        </DialogContent>
      </Dialog>

      <DndContext
        sensors={sensorsContext}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragOver={handleDragOver}
        onDragEnd={handleDragEnd}
      >
        {orderedColumns.length === 0 ? (
          <div className="flex-1 flex items-center justify-center text-gray-400">
            {statusesLoading ? (
              <div className="text-center">
                <div className="text-sm">Loading statuses...</div>
              </div>
            ) : availableStatuses && availableStatuses.length === 0 ? (
              <div className="text-sm">No statuses configured for this board.</div>
            ) : (
              <div className="text-sm">Loading board...</div>
            )}
          </div>
        ) : (
          <SortableContext items={orderedColumns.map((column) => column.orderId)} strategy={horizontalListSortingStrategy}>
            <div className="flex gap-4 overflow-x-auto flex-1 min-h-0 pb-6">
              {orderedColumns.map((column) => (
                <SortableColumn
                  key={column.orderId}
                  column={{ id: column.id, title: column.title }}
                  orderId={column.orderId}
                  tasks={column.tasks as BoardTask[]}
                  onTaskClick={handleTaskClick}
                  draggedColumnId={draggedColumnId}
                  hoveredColumnId={hoveredColumnId}
                />
              ))}
            </div>
          </SortableContext>
        )}

        <DragOverlay dropAnimation={null} modifiers={[snapCenterToCursor]}>
          {draggedColumnId && activeColumnOverlay ? (
            <ColumnDragPreview column={{ id: activeColumnOverlay.id, title: activeColumnOverlay.title }} tasks={activeColumnOverlay.tasks} measurements={dragMeasurements} />
          ) : activeId ? (
            <TaskDragPreview task={tasks.find((task) => String(task.id) === activeId) ?? null} measurements={dragMeasurements} />
          ) : null}
        </DragOverlay>
      </DndContext>

      <TaskDetailsModal
        task={selectedTask}
        open={isTaskModalOpen}
        onClose={() => {
          setIsTaskModalOpen(false);
          setSelectedTask(null);
        }}
        onUpdate={handleUpdateTaskForModal}
        projectId={activeProjectId}
      />
    </div>
  );
}

const arrayEqual = (a: string[], b: string[]) => {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i += 1) {
    if (a[i] !== b[i]) return false;
  }
  return true;
};
