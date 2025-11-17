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
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
  return `${parts[0].charAt(0)}${parts[parts.length - 1].charAt(0)}`.toUpperCase();
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
      className={`flex items-start gap-3 rounded-lg border border-gray-200 bg-white p-3 shadow-sm transition hover:border-gray-300 dark:border-gray-700 dark:bg-gray-900 ${
        isDragging ? "opacity-40" : ""
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
          {task.sprint_id ? (
            <span className="rounded bg-emerald-50 px-2 py-0.5 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-200">
              Sprint: {task.sprint_id}
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

function AssigneeColumn({
  columnKey,
  assigneeId,
  assigneeName,
  tasks,
  totalHours,
  isAssignable,
  isOpen,
  onToggle,
  showDropHint,
}: AssigneeColumnProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: columnKey,
    data: {
      type: "assignee",
      assigneeId,
      isAssignable,
    },
  });

  const dropHintVisible = !isOpen && showDropHint && isAssignable;

  return (
    <div ref={setNodeRef}>
      <Collapsible open={isOpen} onOpenChange={(open) => onToggle(columnKey, open)}>
        <Card
          className={cn(
            "flex min-h-[96px] flex-col rounded-xl border border-gray-200 bg-gray-50/80 p-4 shadow-sm transition dark:border-gray-700 dark:bg-gray-900/60",
            isOver && "border-blue-400 bg-blue-50/60 dark:border-blue-500 dark:bg-blue-900/20",
          )}
        >
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <AvatarBubble name={assigneeName} />
              <div>
                <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                  {assigneeId ? assigneeName : assigneeName || "Unassigned"}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  {tasks.length} task{tasks.length === 1 ? "" : "s"} • {totalHours.toFixed(1)}h
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {assigneeId ? (
                <span className="rounded-full bg-blue-100 px-2 py-1 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-200">
                  {assigneeId}
                </span>
              ) : (
                <span className="rounded-full bg-amber-100 px-2 py-1 text-xs font-medium text-amber-700 dark:bg-amber-900/40 dark:text-amber-200">
                  Unassigned
                </span>
              )}
              <CollapsibleTrigger className="flex items-center gap-1 rounded border border-gray-200 bg-white px-2 py-1 text-xs font-medium text-gray-600 transition hover:bg-gray-100 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700">
                {isOpen ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                {isOpen ? "Collapse" : "Expand"}
              </CollapsibleTrigger>
            </div>
          </div>
          <CollapsibleContent>
            <SortableContext items={tasks.map((task) => task.id)} strategy={verticalListSortingStrategy}>
              {tasks.length === 0 ? (
                <div className="mt-3 rounded border border-dashed border-gray-200 bg-white py-6 text-center text-sm text-gray-400 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-500">
                  {isAssignable ? "Drop tasks here" : "Tasks assigned outside this workspace"}
                </div>
              ) : (
                <div className="mt-3 space-y-2">
                  {tasks.map((task) => (
                    <SortableTask key={task.id} task={task} assigneeId={assigneeId} />
                  ))}
                </div>
              )}
            </SortableContext>
          </CollapsibleContent>
          {dropHintVisible ? (
            <div className="mt-3 rounded border border-dashed border-gray-200 bg-white py-4 text-center text-xs text-gray-400 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-500">
              {isAssignable ? "Drop tasks here" : "Tasks assigned outside this workspace"}
            </div>
          ) : null}
        </Card>
      </Collapsible>
    </div>
  );
}

export function TeamAssignmentsView() {
  const { projectIdForData, activeProject } = useProjectData();
  const { tasks, loading: tasksLoading, error: tasksError, refresh: refreshTasks } = useTasks(projectIdForData ?? undefined);
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
    const unique = new Set<string>();
    tasks.forEach((task) => {
      if (task.sprint_id) unique.add(String(task.sprint_id));
    });
    return Array.from(unique).sort();
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

  if (tasksLoading || usersLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-24" />
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-48 w-full rounded-xl" />
          ))}
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
            {sprintOptions.map((id) => (
              <SelectItem key={id} value={id}>
                {id}
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
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {columns.map((column) => (
            <AssigneeColumn
              key={column.columnKey}
              columnKey={column.columnKey}
              assigneeId={column.assigneeId}
              assigneeName={column.assigneeName}
              tasks={column.tasks}
              totalHours={column.totalHours}
              isAssignable={column.isAssignable}
              isOpen={openColumns[column.columnKey] ?? true}
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

