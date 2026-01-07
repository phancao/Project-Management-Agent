// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  rectIntersection,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import type { DraggableAttributes } from "@dnd-kit/core";
import type { SyntheticListenerMap } from "@dnd-kit/core/dist/hooks/utilities";
import { CSS } from "@dnd-kit/utilities";
import { Inbox, Users, GripVertical, Loader2, ChevronDown, ChevronRight } from "lucide-react";
import { toast } from "sonner";

import { Card } from "~/components/ui/card";
import { Button } from "~/components/ui/button";
import { Skeleton } from "~/components/ui/skeleton";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "~/components/ui/select";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "~/components/ui/collapsible";
import { cn } from "~/lib/utils";

import { useProjectData } from "../../../hooks/use-project-data";
import { useTasks, type Task } from "~/core/api/hooks/pm/use-tasks";
import { useUsers } from "~/core/api/hooks/pm/use-users";
import { resolveServiceURL } from "~/core/api/resolve-service-url";

const UNASSIGNED_KEY = "__unassigned__";

type ActiveDrag = {
  taskId: string;
  fromAssigneeId: string | null;
};

type DragHandleProps = {
  listeners?: SyntheticListenerMap;
  attributes?: DraggableAttributes;
};

type Column = {
  columnKey: string;
  assigneeId: string | null;
  assigneeName: string;
  isAssignable: boolean;
  tasks: Task[];
  totalHours: number;
};

type AssigneeColumnProps = Column & {
  isOpen: boolean;
  onToggle: (key: string, open: boolean) => void;
  showDropHint: boolean;
};

function initials(name?: string | null) {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0]?.charAt(0)?.toUpperCase() ?? "?";
  return `${parts[0]?.charAt(0) ?? ""}${parts[parts.length - 1]?.charAt(0) ?? ""}`.toUpperCase() || "?";
}

function AvatarBubble({ name }: { name: string | null }) {
  return (
    <div className="flex h-10 w-10 items-center justify-center rounded-full border border-gray-300 bg-white text-sm font-semibold uppercase text-gray-700 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200">
      {initials(name)}
    </div>
  );
}

function TaskCard({ task, isDragging, dragHandleProps }: { task: Task; isDragging?: boolean; dragHandleProps?: DragHandleProps }) {
  const listenerProps = dragHandleProps?.listeners ?? {};
  const attributeProps = dragHandleProps?.attributes ?? {};

  return (
    <div
      className={`flex items-start gap-3 rounded-lg border border-gray-200 bg-white p-3 shadow-sm transition hover:border-gray-300 dark:border-gray-700 dark:bg-gray-900 ${isDragging ? "opacity-40" : ""
        }`}
    >
      <div
        className="mt-1 cursor-grab text-gray-400 dark:text-gray-500"
        {...(listenerProps as Record<string, unknown>)}
        {...(attributeProps as Record<string, unknown>)}
      >
        <GripVertical className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-semibold text-gray-900 dark:text-gray-100">
          {task.title}
        </div>
        <div className="mt-1 flex flex-wrap gap-2 text-xs text-gray-500 dark:text-gray-400">
          {task.status ? (
            <span className="rounded bg-blue-50 px-2 py-0.5 text-blue-700 dark:bg-blue-900/40 dark:text-blue-200">
              {task.status}
            </span>
          ) : null}
          {task.priority ? (
            <span className="rounded bg-amber-50 px-2 py-0.5 text-amber-700 dark:bg-amber-900/40 dark:text-amber-200">
              {task.priority}
            </span>
          ) : null}
          {task.sprint_name ? (
            <span className="rounded bg-emerald-50 px-2 py-0.5 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-200">
              {task.sprint_name}
            </span>
          ) : null}
          {typeof task.estimated_hours === "number" ? <span>{Number(task.estimated_hours).toFixed(1)}h</span> : null}
        </div>
      </div>
    </div>
  );
}

function SortableTask({ task, assigneeId }: { task: Task; assigneeId: string | null }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: task.id,
    data: {
      type: "task",
      taskId: task.id,
      assigneeId,
    },
  });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 10 : undefined,
  };

  return (
    <div ref={setNodeRef} style={style}>
      <TaskCard task={task} isDragging={isDragging} dragHandleProps={{ listeners, attributes }} />
    </div>
  );
}

function UserCard({
  columnKey,
  assigneeId,
  assigneeName,
  tasks,
  totalHours,
  maxHours,
  isAssignable,
  isOpen,
  onToggle,
  showDropHint,
}: AssigneeColumnProps & { maxHours: number }) {
  const { setNodeRef, isOver } = useDroppable({
    id: columnKey,
    data: {
      type: "assignee",
      assigneeId,
      isAssignable,
    },
  });

  // Calculate workload percentage relative to the busiest person
  const workloadPercent = maxHours > 0 ? Math.min(100, (totalHours / maxHours) * 100) : 0;

  // Color based on workload level
  const getProgressColor = () => {
    if (workloadPercent >= 80) return "bg-red-500";
    if (workloadPercent >= 60) return "bg-amber-500";
    return "bg-emerald-500";
  };

  return (
    <div
      ref={setNodeRef}
      className={cn(
        "rounded-xl border bg-card shadow-sm transition-all duration-200",
        isOver && "border-blue-400 ring-2 ring-blue-200 dark:ring-blue-800",
        !isOver && "border-border"
      )}
    >
      {/* Main Row - User Info | Progress Bar | Expand Icon */}
      <div
        className="flex items-center gap-4 p-3 cursor-pointer hover:bg-muted/50 transition-colors"
        onClick={() => onToggle(columnKey, !isOpen)}
      >
        {/* Left: Avatar and Name (fixed width) */}
        <div className="flex items-center gap-3 w-[200px] flex-shrink-0">
          <AvatarBubble name={assigneeName} />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold truncate">
                {assigneeName || "Unassigned"}
              </span>
              {!assigneeId && (
                <span className="rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:bg-amber-900/40 dark:text-amber-200">
                  Pool
                </span>
              )}
            </div>
            <div className="text-xs text-muted-foreground">
              {tasks.length} task{tasks.length !== 1 && "s"} • {totalHours.toFixed(0)}h
            </div>
          </div>
        </div>

        {/* Middle: Workload Progress Bar (flex grow) */}
        <div className="flex-1 min-w-[100px]">
          <div className="h-3 w-full rounded-full bg-muted overflow-hidden">
            <div
              className={cn("h-full rounded-full transition-all duration-300", getProgressColor())}
              style={{ width: `${workloadPercent}%` }}
            />
          </div>
          <div className="text-[10px] text-muted-foreground mt-0.5 text-right">
            {workloadPercent.toFixed(0)}% workload
          </div>
        </div>

        {/* Right: Expand Icon */}
        <div className="text-muted-foreground flex-shrink-0">
          {isOpen ? <ChevronDown className="h-5 w-5" /> : <ChevronRight className="h-5 w-5" />}
        </div>
      </div>

      {/* Drop hint when dragging */}
      {showDropHint && isAssignable && !isOpen && (
        <div className="px-3 pb-2">
          <div className="rounded border border-dashed border-blue-300 bg-blue-50/50 py-1.5 text-center text-xs text-blue-500 dark:border-blue-700 dark:bg-blue-900/20 dark:text-blue-400">
            Drop to assign
          </div>
        </div>
      )}

      {/* Expandable Task List */}
      {isOpen && (
        <div className="px-3 pb-3 border-t border-border/50">
          <SortableContext items={tasks.map((task) => task.id)} strategy={verticalListSortingStrategy}>
            {tasks.length === 0 ? (
              <div className="mt-2 rounded border border-dashed border-muted-foreground/30 bg-muted/30 py-4 text-center text-xs text-muted-foreground">
                {isAssignable ? "Drop tasks here" : "No tasks"}
              </div>
            ) : (
              <div className="mt-2 max-h-[240px] overflow-y-auto grid gap-2 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {tasks.map((task) => (
                  <SortableTask key={task.id} task={task} assigneeId={assigneeId} />
                ))}
              </div>
            )}
          </SortableContext>
        </div>
      )}
    </div>
  );
}

export function TeamAssignmentsView() {
  const { projectIdForData, activeProject } = useProjectData();
  const { tasks, loading: tasksLoading, isFetching: tasksFetching, error: tasksError, refresh: refreshTasks } = useTasks(projectIdForData ?? undefined);
  const { users, loading: usersLoading, error: usersError } = useUsers(projectIdForData ?? undefined);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    }),
  );

  const [activeDrag, setActiveDrag] = useState<ActiveDrag | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [filterSprint, setFilterSprint] = useState<string>("all");

  const userNameById = useMemo(() => {
    const map = new Map<string, string>();
    users.forEach((user) => {
      const fallback = user.username || user.email || user.id;
      map.set(user.id, user.name || fallback);
    });
    return map;
  }, [users]);

  const userOptions = useMemo(() => {
    return Array.from(userNameById.entries())
      .map(([id, name]) => ({ id, name }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [userNameById]);

  const filteredTasks = useMemo(() => {
    return tasks.filter((task) => {
      if (filterStatus !== "all" && task.status?.toLowerCase() !== filterStatus) {
        return false;
      }
      if (filterSprint !== "all" && String(task.sprint_id ?? "") !== filterSprint) {
        return false;
      }
      return true;
    });
  }, [tasks, filterStatus, filterSprint]);

  const sprintOptions = useMemo(() => {
    const sprintMap = new Map<string, string>();
    tasks.forEach((task) => {
      if (task.sprint_id) {
        const name = task.sprint_name || task.sprint_id;
        sprintMap.set(String(task.sprint_id), name);
      }
    });
    return Array.from(sprintMap.entries())
      .map(([id, name]) => ({ id, name }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [tasks]);

  const statusOptions = useMemo(() => {
    const unique = new Set<string>();
    tasks.forEach((task) => {
      if (task.status) unique.add(task.status.toLowerCase());
    });
    return Array.from(unique).sort();
  }, [tasks]);

  const columns = useMemo<Column[]>(() => {
    const columnMap = new Map<string, Column>();

    const ensureColumn = (columnKey: string, assigneeId: string | null, assigneeName: string, isAssignable: boolean) => {
      const existing = columnMap.get(columnKey);
      if (existing) {
        return existing;
      }

      const column: Column = {
        columnKey,
        assigneeId,
        assigneeName,
        isAssignable,
        tasks: [],
        totalHours: 0,
      };
      columnMap.set(columnKey, column);
      return column;
    };

    filteredTasks.forEach((task) => {
      const assigneeId = task.assignee_id ? String(task.assignee_id) : null;
      const assigneeName = assigneeId
        ? userNameById.get(assigneeId) ?? task.assigned_to ?? assigneeId
        : task.assigned_to ?? "Unassigned";
      const columnKey =
        assigneeId ??
        (task.assigned_to ? `name:${task.assigned_to}` : UNASSIGNED_KEY);
      const isAssignable = assigneeId !== null || columnKey === UNASSIGNED_KEY;

      const column = ensureColumn(columnKey, assigneeId, assigneeName, isAssignable);
      column.tasks.push(task);
      column.totalHours += Number(task.estimated_hours ?? 0);
    });

    ensureColumn(UNASSIGNED_KEY, null, "Unassigned", true);

    return Array.from(columnMap.values()).sort((a, b) => {
      if (a.columnKey === UNASSIGNED_KEY) return 1;
      if (b.columnKey === UNASSIGNED_KEY) return -1;
      return b.totalHours - a.totalHours || a.assigneeName.localeCompare(b.assigneeName);
    });
  }, [filteredTasks, userNameById]);

  // Calculate max hours for workload comparison bar
  const maxHours = useMemo(() => {
    return Math.max(...columns.map(c => c.totalHours), 1);
  }, [columns]);

  const taskMap = useMemo(() => {
    const map = new Map<string, Task>();
    tasks.forEach((task) => {
      map.set(task.id, task);
    });
    return map;
  }, [tasks]);

  const handleAssign = useCallback(
    async (taskId: string, newAssigneeId: string | null) => {
      if (!projectIdForData) return;
      setIsSaving(true);
      try {
        const url = resolveServiceURL(`pm/projects/${projectIdForData}/tasks/${taskId}/assign-user`);
        const response = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ assignee_id: newAssigneeId }),
        });
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(errorText || "Failed to reassign task");
        }
        await refreshTasks(false);
        const assignedName = newAssigneeId ? userNameById.get(newAssigneeId) ?? newAssigneeId : null;
        toast.success("Task reassigned", {
          description: assignedName ? `Task is now assigned to ${assignedName}.` : "Task moved to Unassigned.",
        });
      } catch (error) {
        const message = error instanceof Error ? error.message : "Unknown error";
        toast.error("Failed to reassign task", { description: message });
      } finally {
        setIsSaving(false);
      }
    },
    [projectIdForData, refreshTasks, userNameById],
  );

  const handleDragStart = useCallback((event: DragStartEvent) => {
    const taskId = event.active.data.current?.taskId as string | undefined;
    const assigneeId = (event.active.data.current?.assigneeId as string | null | undefined) ?? null;
    if (!taskId) return;
    setActiveDrag({ taskId, fromAssigneeId: assigneeId });
  }, []);

  const handleDragEnd = useCallback(
    async (event: DragEndEvent) => {
      const overData = event.over?.data?.current as { assigneeId?: string | null; isAssignable?: boolean } | undefined;
      if (!activeDrag) {
        setActiveDrag(null);
        return;
      }

      if (!overData || overData.isAssignable === false) {
        setActiveDrag(null);
        return;
      }

      const newAssigneeId = overData.assigneeId ?? null;
      if (newAssigneeId === activeDrag.fromAssigneeId) {
        setActiveDrag(null);
        return;
      }

      await handleAssign(activeDrag.taskId, newAssigneeId);
      setActiveDrag(null);
    },
    [activeDrag, handleAssign],
  );

  const [openColumns, setOpenColumns] = useState<Record<string, boolean>>({});

  useEffect(() => {
    setOpenColumns((prev) => {
      const next: Record<string, boolean> = {};
      columns.forEach((column) => {
        next[column.columnKey] = prev[column.columnKey] ?? true;
      });
      return next;
    });
  }, [columns]);

  const handleToggleColumn = useCallback((columnKey: string, open: boolean) => {
    setOpenColumns((prev) => ({ ...prev, [columnKey]: open }));
  }, []);

  if (tasksLoading || tasksFetching || usersLoading) {
    // Calculate loading progress
    const loadingItems = [
      { label: "Tasks", isLoading: tasksLoading, count: tasks?.length || 0 },
      { label: "Users", isLoading: usersLoading, count: users?.length || 0 },
    ];
    const completedCount = loadingItems.filter(item => !item.isLoading).length;
    const progressPercent = Math.round((completedCount / loadingItems.length) * 100);

    return (
      <div className="h-full w-full flex items-center justify-center bg-muted/20 p-4">
        <div className="bg-card border rounded-xl shadow-lg p-5 w-full max-w-sm">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold flex items-center gap-2">
              <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                <Users className="w-4 h-4 animate-pulse text-blue-600 dark:text-blue-400" />
              </div>
              Loading Team
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
                  {index === 0 ? <Inbox className="w-3.5 h-3.5 text-green-500" /> : <Users className="w-3.5 h-3.5 text-blue-500" />}
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
            Loading tasks and team members...
          </p>
        </div>
      </div>
    );
  }

  // Check if usersError is a permission error
  const isPermissionError = usersError && (
    usersError.message.includes("403") ||
    usersError.message.includes("Forbidden") ||
    usersError.message.includes("401") ||
    usersError.message.includes("Unauthorized")
  );

  if (tasksError) {
    return (
      <Card className="p-6 text-center text-rose-600 dark:text-rose-300">
        Failed to load team assignments: {tasksError.message}
      </Card>
    );
  }

  if (usersError && !isPermissionError) {
    return (
      <Card className="p-6 text-center text-rose-600 dark:text-rose-300">
        Failed to load team assignments: {usersError.message}
      </Card>
    );
  }

  if (isPermissionError) {
    return (
      <Card className="p-6 text-center">
        <div className="mx-auto max-w-md space-y-4">
          <div className="flex justify-center">
            <div className="rounded-full bg-amber-100 p-3 dark:bg-amber-900/30">
              <Users className="h-6 w-6 text-amber-600 dark:text-amber-400" />
            </div>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Cannot View Team Assignments
            </h3>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
              Your API key doesn't have permission to access the users endpoint.
              Please contact your administrator to grant the necessary permissions,
              or use an API key with user access rights.
            </p>
          </div>
        </div>
      </Card>
    );
  }

  const isDraggingTask = Boolean(activeDrag);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Team Assignments</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">{activeProject?.name ?? "Selected project"}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
          <span className="flex items-center gap-1">
            <Users className="h-4 w-4" />
            {userOptions.length} team members
          </span>
          <span className="flex items-center gap-1">
            <Inbox className="h-4 w-4" />
            {tasks.length} total tasks
          </span>
          {isSaving ? (
            <span className="flex items-center gap-1 text-blue-600 dark:text-blue-300">
              <Loader2 className="h-4 w-4 animate-spin" />
              Syncing...
            </span>
          ) : null}
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <Select value={filterSprint} onValueChange={setFilterSprint}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Sprint" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All sprints</SelectItem>
            {sprintOptions.map((sprint) => (
              <SelectItem key={sprint.id} value={sprint.id}>
                {sprint.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={filterStatus} onValueChange={setFilterStatus}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            {statusOptions.map((status) => (
              <SelectItem key={status} value={status}>
                {status}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            setFilterSprint("all");
            setFilterStatus("all");
          }}
          className="text-xs"
        >
          Reset Filters
        </Button>
      </div>

      <DndContext
        sensors={sensors}
        collisionDetection={rectIntersection}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div className="space-y-3">
          {columns.map((column) => (
            <UserCard
              key={column.columnKey}
              columnKey={column.columnKey}
              assigneeId={column.assigneeId}
              assigneeName={column.assigneeName}
              tasks={column.tasks}
              totalHours={column.totalHours}
              maxHours={maxHours}
              isAssignable={column.isAssignable}
              isOpen={openColumns[column.columnKey] ?? false}
              onToggle={handleToggleColumn}
              showDropHint={isDraggingTask}
            />
          ))}
        </div>

        <DragOverlay>
          {activeDrag ? (
            <div className="max-w-md rounded-xl border border-blue-400 bg-white p-3 shadow-2xl dark:border-blue-600 dark:bg-gray-900">
              {taskMap.get(activeDrag.taskId) ? (
                <TaskCard task={taskMap.get(activeDrag.taskId)!} isDragging />
              ) : null}
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>
    </div>
  );
}

