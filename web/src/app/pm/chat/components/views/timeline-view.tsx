// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  CalendarRange,
  ListChecks,
  Users,
} from "lucide-react";

import { Badge } from "~/components/ui/badge";
import { Card } from "~/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "~/components/ui/select";
import { Skeleton } from "~/components/ui/skeleton";

import { useProjectData } from "../../../hooks/use-project-data";
import { useSprints, type Sprint } from "~/core/api/hooks/pm/use-sprints";
import { useTasks, type Task } from "~/core/api/hooks/pm/use-tasks";
import { useEpics, type Epic } from "~/core/api/hooks/pm/use-epics";
import { useUsers } from "~/core/api/hooks/pm/use-users";

const DAY_IN_MS = 1000 * 60 * 60 * 24;
const MIN_BAR_PERCENT = 2;
const UNASSIGNED_KEY = "__unassigned__";

const shortDateFormatter = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "numeric",
});

const longDateFormatter = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "numeric",
  year: "numeric",
});

type TimelineItemType = "sprint" | "task";

type TimelineItem = {
  id: string;
  label: string;
  subLabel?: string;
  type: TimelineItemType;
  startDate: Date;
  endDate: Date;
  color: string;
  status?: string;
  statusLabel?: string;
  statusValue?: string;
  sprintId?: string | null;
  sprintName?: string | null;
  assigneeKey?: string | null;
  assigneeName?: string | null;
  tooltip?: string;
};

type MissingSprintInfo = {
  sprint: Sprint;
  reason: "missing_start" | "missing_end" | "invalid_range";
};

type MissingTaskInfo = {
  task: Task;
  reason: "missing_start" | "missing_end" | "invalid_range";
};

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function addDays(date: Date, days: number) {
  const result = new Date(date);
  result.setDate(result.getDate() + days);
  return result;
}

function parseDate(value?: string | null): Date | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatDateShort(date: Date) {
  return shortDateFormatter.format(date);
}

function formatDateLong(date: Date) {
  return longDateFormatter.format(date);
}

function formatDateRange(start: Date, end: Date) {
  return `${formatDateLong(start)} → ${formatDateLong(end)}`;
}

function formatStatusLabel(value?: string | null) {
  if (!value) return "Unknown";
  return value
    .toLowerCase()
    .split(/[\s_]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function describeMissingSprint(reason: MissingSprintInfo["reason"]) {
  switch (reason) {
    case "missing_start":
      return "Start date missing";
    case "missing_end":
      return "End date missing";
    case "invalid_range":
      return "End date occurs before the start date";
    default:
      return "Date information missing";
  }
}

function describeMissingTask(reason: MissingTaskInfo["reason"]) {
  switch (reason) {
    case "missing_start":
      return "Start date missing";
    case "missing_end":
      return "Due date missing";
    case "invalid_range":
      return "Due date occurs before the start date";
    default:
      return "Date information missing";
  }
}

const SPRINT_STATUS_COLORS: Record<string, string> = {
  active: "#2563eb",
  future: "#0ea5e9",
  closed: "#94a3b8",
  planned: "#6366f1",
  default: "#64748b",
};

const TASK_STATUS_COLORS: Record<string, string> = {
  todo: "#f59e0b",
  backlog: "#6366f1",
  in_progress: "#2563eb",
  in_review: "#ea580c",
  blocked: "#a855f7",
  done: "#22c55e",
  completed: "#16a34a",
};

const TASK_PRIORITY_COLORS: Record<string, string> = {
  critical: "#7c3aed",
  highest: "#ef4444",
  high: "#ef4444",
  medium: "#f59e0b",
  low: "#3b82f6",
  lowest: "#06b6d4",
};

function getTaskColor(task: Task) {
  const status = task.status?.toLowerCase() ?? "";
  const priority = task.priority?.toLowerCase() ?? "";

  if (status in TASK_STATUS_COLORS) {
    return TASK_STATUS_COLORS[status];
  }
  if (priority in TASK_PRIORITY_COLORS) {
    return TASK_PRIORITY_COLORS[priority];
  }

  return "#6366f1";
}

function getSprintColor(sprint: Sprint) {
  const status = sprint.status?.toLowerCase() ?? "";
  return SPRINT_STATUS_COLORS[status] ?? SPRINT_STATUS_COLORS.default;
}

interface TimelineChartProps {
  items: TimelineItem[];
  minDate: Date;
  maxDate: Date;
  todayPercent: number | null;
}

function TimelineChart({ items, minDate, maxDate, todayPercent }: TimelineChartProps) {
  const totalRange = Math.max(maxDate.getTime() - minDate.getTime(), DAY_IN_MS);

  return (
    <div className="space-y-3">
      {items.map((item) => {
        const startOffset = item.startDate.getTime() - minDate.getTime();
        const endTime = Math.max(item.endDate.getTime(), item.startDate.getTime());
        const endOffset = endTime - minDate.getTime();

        let leftPercent = clamp((startOffset / totalRange) * 100, 0, 100);
        let widthPercent = clamp(((endOffset - startOffset) / totalRange) * 100, MIN_BAR_PERCENT, 100);

        if (leftPercent + widthPercent > 100) {
          widthPercent = Math.max(MIN_BAR_PERCENT, 100 - leftPercent);
        }

        const rangeLabel = formatDateRange(item.startDate, item.endDate);

        return (
          <div
            key={`${item.type}-${item.id}`}
            className="grid grid-cols-[220px_minmax(0,1fr)_150px] items-center gap-4 rounded-md border border-transparent p-2 hover:border-gray-200 hover:bg-gray-50 dark:hover:border-gray-700 dark:hover:bg-gray-800/40 transition-colors"
          >
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                  {item.label}
                </span>
                {item.type === "task" && item.statusLabel ? (
                  <Badge variant="outline" className="text-[11px] capitalize">
                    {item.statusLabel}
                  </Badge>
                ) : null}
                {item.type === "sprint" ? (
                  <Badge variant="outline" className="text-[11px] capitalize">
                    Sprint
                  </Badge>
                ) : null}
              </div>
              {item.subLabel ? (
                <div className="text-xs text-gray-500 dark:text-gray-400">{item.subLabel}</div>
              ) : null}
            </div>
            <div className="relative h-8 rounded bg-gray-100 dark:bg-gray-800" title={item.tooltip ?? rangeLabel}>
              {todayPercent !== null ? (
                <div
                  aria-hidden
                  className="absolute top-0 bottom-0 w-[2px] bg-rose-500/80 dark:bg-rose-400/80 pointer-events-none"
                  style={{ left: `${clamp(todayPercent, 0, 100)}%` }}
                />
              ) : null}
              <div
                className="absolute top-1 bottom-1 flex items-center overflow-hidden rounded text-xs font-medium text-white shadow-sm"
                style={{
                  left: `${leftPercent}%`,
                  width: `${widthPercent}%`,
                  backgroundColor: item.color,
                }}
              >
                <span className="px-2 truncate">{item.type === "task" ? formatStatusLabel(item.status) : item.statusLabel}</span>
              </div>
            </div>
            <div className="text-xs font-medium text-right text-gray-500 dark:text-gray-400">
              {rangeLabel}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function TimelineView() {
  const { activeProject, projectIdForData, projectsLoading } = useProjectData();
  const projectId = projectIdForData ?? "";

  const { sprints, loading: sprintsLoading, error: sprintsError } = useSprints(projectId);
  const { tasks, loading: tasksLoading, error: tasksError } = useTasks(projectIdForData ?? undefined);
  const { epics } = useEpics(projectIdForData);
  const { users } = useUsers(projectIdForData ?? undefined);

  const [sprintFilter, setSprintFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [assigneeFilter, setAssigneeFilter] = useState<string>("all");

  useEffect(() => {
    setSprintFilter("all");
    setStatusFilter("all");
    setAssigneeFilter("all");
  }, [projectIdForData]);

  const userMap = useMemo(() => {
    const map = new Map<string, string>();
    users.forEach((user) => {
      map.set(user.id, user.name || user.username || user.email || user.id);
    });
    return map;
  }, [users]);

  const sprintMap = useMemo(() => {
    const map = new Map<string, Sprint>();
    sprints.forEach((sprint) => {
      map.set(sprint.id, sprint);
    });
    return map;
  }, [sprints]);

  const epicMap = useMemo(() => {
    const map = new Map<string, Epic>();
    epics.forEach((epic) => {
      map.set(epic.id, epic);
    });
    return map;
  }, [epics]);

  const timeline = useMemo(() => {
    const timelineItems: TimelineItem[] = [];
    const missingSprints: MissingSprintInfo[] = [];
    const missingTasks: MissingTaskInfo[] = [];

    sprints.forEach((sprint) => {
      const start = parseDate(sprint.start_date);
      const end = parseDate(sprint.end_date);

      if (!start && !end) {
        missingSprints.push({ sprint, reason: "missing_start" });
        missingSprints.push({ sprint, reason: "missing_end" });
        return;
      }

      if (!start) {
        missingSprints.push({ sprint, reason: "missing_start" });
        return;
      }

      if (!end) {
        missingSprints.push({ sprint, reason: "missing_end" });
        return;
      }

      if (end.getTime() < start.getTime()) {
        missingSprints.push({ sprint, reason: "invalid_range" });
        return;
      }

      timelineItems.push({
        id: sprint.id,
        label: sprint.name,
        type: "sprint",
        startDate: start,
        endDate: end,
        color: getSprintColor(sprint),
        status: sprint.status,
        statusValue: sprint.status?.toLowerCase(),
        statusLabel: formatStatusLabel(sprint.status),
        sprintId: sprint.id,
        sprintName: sprint.name,
        tooltip: `Sprint ${sprint.name} • ${formatDateRange(start, end)}`,
      });
    });

    tasks.forEach((task) => {
      const start = parseDate(task.start_date);
      const end = parseDate(task.due_date);

      if (!start && !end) {
        missingTasks.push({ task, reason: "missing_start" });
        missingTasks.push({ task, reason: "missing_end" });
        return;
      }

      if (!start) {
        missingTasks.push({ task, reason: "missing_start" });
        return;
      }

      if (!end) {
        missingTasks.push({ task, reason: "missing_end" });
        return;
      }

      if (end.getTime() < start.getTime()) {
        missingTasks.push({ task, reason: "invalid_range" });
        return;
      }

      const sprint = task.sprint_id ? sprintMap.get(task.sprint_id) : undefined;
      const epic = task.epic_id ? epicMap.get(task.epic_id) : undefined;
      const statusValue = task.status?.toLowerCase() ?? "unknown";
      const assigneeKey = task.assignee_id ?? (task.assigned_to ? `name:${task.assigned_to}` : UNASSIGNED_KEY);
      const assigneeName =
        task.assigned_to ||
        (task.assignee_id ? userMap.get(task.assignee_id) ?? task.assignee_id : null) ||
        null;

      const subLabelParts: string[] = [];
      if (sprint?.name) subLabelParts.push(`Sprint: ${sprint.name}`);
      if (epic?.name) subLabelParts.push(`Epic: ${epic.name}`);
      subLabelParts.push(`Assignee: ${assigneeName ?? "Unassigned"}`);

      timelineItems.push({
        id: task.id,
        label: task.title,
        type: "task",
        startDate: start,
        endDate: end,
        color: getTaskColor(task),
        status: task.status,
        statusValue,
        statusLabel: formatStatusLabel(task.status),
        sprintId: task.sprint_id ?? null,
        sprintName: sprint?.name ?? null,
        assigneeKey,
        assigneeName,
        subLabel: subLabelParts.join(" • "),
        tooltip: [
          task.title,
          `Status: ${formatStatusLabel(task.status)}`,
          sprint?.name ? `Sprint: ${sprint.name}` : null,
          epic?.name ? `Epic: ${epic.name}` : null,
          `Assignee: ${assigneeName ?? "Unassigned"}`,
          `Duration: ${formatDateRange(start, end)}`,
        ]
          .filter(Boolean)
          .join("\n"),
      });
    });

    const sortedItems = timelineItems.sort(
      (a, b) => a.startDate.getTime() - b.startDate.getTime()
    );

    const dates = sortedItems.flatMap((item) => [
      item.startDate.getTime(),
      item.endDate.getTime(),
    ]);

    if (dates.length === 0) {
      return {
        sprintItems: [] as TimelineItem[],
        taskItems: [] as TimelineItem[],
        minDate: null as Date | null,
        maxDate: null as Date | null,
        missingSprints,
        missingTasks,
      };
    }

    const minDate = addDays(new Date(Math.min(...dates)), -2);
    const maxDate = addDays(new Date(Math.max(...dates)), 2);

    return {
      sprintItems: sortedItems.filter((item) => item.type === "sprint"),
      taskItems: sortedItems.filter((item) => item.type === "task"),
      minDate,
      maxDate,
      missingSprints,
      missingTasks,
    };
  }, [sprints, tasks, sprintMap, epicMap, userMap]);

  const statusOptions = useMemo(() => {
    const values = new Map<string, string>();
    tasks.forEach((task) => {
      if (!task.status) return;
      const value = task.status.toLowerCase();
      if (!values.has(value)) {
        values.set(value, formatStatusLabel(task.status));
      }
    });
    return Array.from(values.entries()).map(([value, label]) => ({ value, label }));
  }, [tasks]);

  const sprintOptions = useMemo(() => {
    return sprints.map((sprint) => ({
      value: sprint.id,
      label: sprint.name,
    }));
  }, [sprints]);

  const assigneeOptions = useMemo(() => {
    const map = new Map<string, string>();
    tasks.forEach((task) => {
      const key = task.assignee_id ?? (task.assigned_to ? `name:${task.assigned_to}` : UNASSIGNED_KEY);
      const name =
        task.assigned_to ||
        (task.assignee_id ? userMap.get(task.assignee_id) ?? task.assignee_id : null) ||
        null;

      if (!map.has(key)) {
        map.set(key, name ?? "Unassigned");
      }
    });

    if (!map.has(UNASSIGNED_KEY)) {
      map.set(UNASSIGNED_KEY, "Unassigned");
    }

    return Array.from(map.entries()).map(([value, label]) => ({ value, label }));
  }, [tasks, userMap]);

  const filteredTaskItems = useMemo(() => {
    let items = timeline.taskItems;
    if (sprintFilter !== "all") {
      items = items.filter((item) => item.sprintId === sprintFilter);
    }
    if (statusFilter !== "all") {
      items = items.filter((item) => item.statusValue === statusFilter);
    }
    if (assigneeFilter !== "all") {
      if (assigneeFilter === UNASSIGNED_KEY) {
        items = items.filter((item) => !item.assigneeKey || item.assigneeKey === UNASSIGNED_KEY);
      } else {
        items = items.filter((item) => item.assigneeKey === assigneeFilter);
      }
    }
    return items;
  }, [timeline.taskItems, sprintFilter, statusFilter, assigneeFilter]);

  const unscheduledTaskCount = timeline.missingTasks.length;
  const unscheduledTasksToDisplay = timeline.missingTasks.slice(0, 6);
  const remainingUnscheduleCount = Math.max(0, unscheduledTaskCount - unscheduledTasksToDisplay.length);

  const timelineRangeDays =
    timeline.minDate && timeline.maxDate
      ? Math.max(1, Math.round((timeline.maxDate.getTime() - timeline.minDate.getTime()) / DAY_IN_MS))
      : null;

  const today = new Date();
  const todayPercent =
    timeline.minDate &&
    timeline.maxDate &&
    today >= timeline.minDate &&
    today <= timeline.maxDate
      ? ((today.getTime() - timeline.minDate.getTime()) /
          (timeline.maxDate.getTime() - timeline.minDate.getTime())) *
        100
      : null;

  const isLoading =
    projectsLoading ||
    (!!projectIdForData && (sprintsLoading || tasksLoading));

  const combinedErrors = [sprintsError, tasksError].filter(Boolean) as Error[];

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-36 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!projectIdForData) {
    return (
      <Card className="p-6">
        <div className="space-y-2 text-center">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            Timeline
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Select a project from the header to view its delivery timeline.
          </p>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Timeline</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {activeProject ? activeProject.name : "Selected project"} •{" "}
            {timeline.minDate && timeline.maxDate
              ? `${formatDateLong(timeline.minDate)} → ${formatDateLong(timeline.maxDate)}`
              : "No scheduled items yet"}
          </p>
        </div>
        <div className="text-xs text-gray-500 dark:text-gray-400">
          The timeline updates automatically when tasks or sprints change.
        </div>
      </div>

      {combinedErrors.length > 0 ? (
        <Card className="border border-rose-300 bg-rose-50/80 dark:border-rose-500/40 dark:bg-rose-500/10 p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-rose-600 dark:text-rose-400" />
            <div>
              <p className="text-sm font-semibold text-rose-700 dark:text-rose-300">
                We couldn't load everything for the timeline.
              </p>
              <ul className="mt-2 space-y-1 text-sm text-rose-600 dark:text-rose-200">
                {combinedErrors.map((err, index) => (
                  <li key={index}>{err.message}</li>
                ))}
              </ul>
            </div>
          </div>
        </Card>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-100 text-blue-600 dark:bg-blue-500/20 dark:text-blue-300">
              <CalendarRange className="h-4 w-4" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                Scheduled Sprints
              </p>
              <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {timeline.sprintItems.length}
                <span className="text-sm font-normal text-gray-400 dark:text-gray-500">
                  {" "}
                  / {sprints.length}
                </span>
              </p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-100 text-indigo-600 dark:bg-indigo-500/20 dark:text-indigo-300">
              <ListChecks className="h-4 w-4" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                Tasks on the timeline
              </p>
              <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {timeline.taskItems.length}
                <span className="text-sm font-normal text-gray-400 dark:text-gray-500">
                  {" "}
                  / {tasks.length}
                </span>
              </p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-100 text-amber-600 dark:bg-amber-500/20 dark:text-amber-300">
              <Users className="h-4 w-4" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                Unscheduled Tasks
              </p>
              <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {unscheduledTaskCount}
              </p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-100 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-300">
              <CalendarRange className="h-4 w-4" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                Timeline Span
              </p>
              <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {timelineRangeDays ? `${timelineRangeDays} days` : "—"}
              </p>
            </div>
          </div>
        </Card>
      </div>

      {(timeline.missingSprints.length > 0 || timeline.missingTasks.length > 0) && (
        <Card className="border border-amber-300 bg-amber-50/60 dark:border-amber-500/40 dark:bg-amber-950/30 p-5">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-amber-600 dark:text-amber-300 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-amber-700 dark:text-amber-200">
                Some items are missing schedule information
              </p>
              <p className="mt-1 text-xs text-amber-700/80 dark:text-amber-200/80">
                Add start and due dates to include them in the timeline.
              </p>

              {timeline.missingSprints.length > 0 ? (
                <div className="mt-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-amber-600 dark:text-amber-300">
                    Sprints missing dates ({timeline.missingSprints.length})
                  </p>
                  <ul className="mt-1 space-y-1 text-sm text-amber-700 dark:text-amber-100">
                    {timeline.missingSprints.slice(0, 4).map(({ sprint, reason }) => (
                      <li key={sprint.id}>
                        <span className="font-medium">{sprint.name}</span> — {describeMissingSprint(reason)}
                      </li>
                    ))}
                    {timeline.missingSprints.length > 4 ? (
                      <li className="text-xs text-amber-600/80 dark:text-amber-200/70">
                        + {timeline.missingSprints.length - 4} more sprints
                      </li>
                    ) : null}
                  </ul>
                </div>
              ) : null}

              {timeline.missingTasks.length > 0 ? (
                <div className="mt-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-amber-600 dark:text-amber-300">
                    Tasks missing dates ({timeline.missingTasks.length})
                  </p>
                  <ul className="mt-1 space-y-1 text-sm text-amber-700 dark:text-amber-100">
                    {unscheduledTasksToDisplay.map(({ task, reason }) => (
                      <li key={task.id}>
                        <span className="font-medium">{task.title}</span> — {describeMissingTask(reason)}
                      </li>
                    ))}
                    {remainingUnscheduleCount > 0 ? (
                      <li className="text-xs text-amber-600/80 dark:text-amber-200/70">
                        + {remainingUnscheduleCount} more tasks
                      </li>
                    ) : null}
                  </ul>
                </div>
              ) : null}
            </div>
          </div>
        </Card>
      )}

      <Card className="p-6 space-y-5">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Sprint schedule</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Visualises the cadence of your sprints with a marker for today.
            </p>
          </div>
          <div className="flex flex-wrap gap-3 text-xs text-gray-500 dark:text-gray-400">
            <div className="flex items-center gap-2">
              <span className="inline-block h-2 w-4 rounded bg-[#2563eb]" />
              Active
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-block h-2 w-4 rounded bg-[#0ea5e9]" />
              Future
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-block h-2 w-4 rounded bg-[#94a3b8]" />
              Closed
            </div>
          </div>
        </div>

        {timeline.sprintItems.length === 0 ? (
          <div className="rounded border border-dashed border-gray-300 bg-gray-50 py-12 text-center text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-900">
            No sprints have scheduling information yet.
          </div>
        ) : timeline.minDate && timeline.maxDate ? (
          <TimelineChart
            items={timeline.sprintItems}
            minDate={timeline.minDate}
            maxDate={timeline.maxDate}
            todayPercent={todayPercent}
          />
        ) : null}
      </Card>

      <Card className="p-6 space-y-5">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Task schedule</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Tasks with start and due dates appear here. Use the filters to focus on a sprint, status, or assignee.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {sprintOptions.length > 0 ? (
              <Select value={sprintFilter} onValueChange={setSprintFilter}>
                <SelectTrigger className="w-[160px]">
                  <SelectValue placeholder="Sprint" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All sprints</SelectItem>
                  {sprintOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : null}

            {statusOptions.length > 0 ? (
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[160px]">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All statuses</SelectItem>
                  {statusOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : null}

            {assigneeOptions.length > 0 ? (
              <Select value={assigneeFilter} onValueChange={setAssigneeFilter}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Assignee" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All assignees</SelectItem>
                  {assigneeOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : null}
          </div>
        </div>

        {timeline.taskItems.length === 0 ? (
          <div className="rounded border border-dashed border-gray-300 bg-gray-50 py-12 text-center text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-900">
            No tasks have start and due dates yet. Schedule tasks to visualise their delivery window.
          </div>
        ) : filteredTaskItems.length === 0 ? (
          <div className="rounded border border-dashed border-gray-300 bg-gray-50 py-12 text-center text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-900">
            No tasks match the current filters.
          </div>
        ) : timeline.minDate && timeline.maxDate ? (
          <TimelineChart
            items={filteredTaskItems}
            minDate={timeline.minDate}
            maxDate={timeline.maxDate}
            todayPercent={todayPercent}
          />
        ) : null}
      </Card>
    </div>
  );
}
