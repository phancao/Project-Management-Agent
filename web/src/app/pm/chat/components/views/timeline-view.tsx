// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { useMemo, useState } from "react";
import {
  AlertCircle,
  CalendarRange,
  ListChecks,
  Users,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from "recharts";

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
import {
  useTimeline,
  type ProjectTimelineResponse,
  type TimelineSprint,
  type TimelineTask,
} from "~/core/api/hooks/pm/use-timeline";

const DAY_IN_MS = 1000 * 60 * 60 * 24;
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

function formatDateShort(date: Date) {
  return shortDateFormatter.format(date);
}

function formatDateLong(date: Date) {
  return longDateFormatter.format(date);
}

function addDays(base: Date, days: number) {
  const next = new Date(base);
  next.setDate(next.getDate() + days);
  return next;
}

function parseISO(value: string | null | undefined): Date | null {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function formatStatusLabel(value?: string | null) {
  if (!value) return "Unknown";
  return value
    .toLowerCase()
    .split(/[\s_]+/)
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

function describeMissing(reason?: string | null) {
  switch (reason) {
    case "missing_start":
      return "Start date missing";
    case "missing_end":
      return "End date missing";
    case "missing_start_end":
      return "Start and end dates missing";
    case "invalid_range":
      return "End date occurs before the start date";
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

function getSprintColor(sprint: TimelineSprint): string {
  const status = sprint.status?.toLowerCase() ?? "";
  return SPRINT_STATUS_COLORS[status] ?? SPRINT_STATUS_COLORS.default ?? "#64748b";
}

function getTaskColor(task: TimelineTask): string {
  const status = task.status?.toLowerCase() ?? "";
  const priority = task.priority?.toLowerCase() ?? "";
  if (status) {
    const color = TASK_STATUS_COLORS[status];
    if (color) return color;
  }
  if (priority) {
    const color = TASK_PRIORITY_COLORS[priority];
    if (color) return color;
  }
  return "#6366f1";
}

type ChartDatum = {
  key: string;
  name: string;
  startOffset: number;
  duration: number;
  color: string;
  details: Record<string, string | null | undefined>;
};

function buildChartData<T extends TimelineSprint | TimelineTask>(
  items: T[],
  getStart: (item: T) => Date | null,
  getEnd: (item: T) => Date | null,
  getColor: (item: T) => string,
  getDetails: (item: T, start: Date, end: Date) => Record<string, string | null | undefined>,
) {
  const scheduled = items.filter((item) => item.is_scheduled);
  if (scheduled.length === 0) {
    return { data: [] as ChartDatum[], minDate: null as Date | null, totalDays: 0 };
  }

  const startValues: number[] = [];
  const endValues: number[] = [];

  scheduled.forEach((item) => {
    const start = getStart(item);
    const end = getEnd(item);
    if (!start || !end) return;
    startValues.push(start.getTime());
    endValues.push(end.getTime());
  });

  if (startValues.length === 0 || endValues.length === 0) {
    return { data: [] as ChartDatum[], minDate: null, totalDays: 0 };
  }

  const minDate = addDays(new Date(Math.min(...startValues)), -1);
  const maxDate = addDays(new Date(Math.max(...endValues)), 1);
  const totalDays = Math.max(1, Math.round((maxDate.getTime() - minDate.getTime()) / DAY_IN_MS));

  const data = scheduled.map((item) => {
    const start = getStart(item)!;
    const end = getEnd(item)!;
    const startOffset = Math.max(0, Math.round((start.getTime() - minDate.getTime()) / DAY_IN_MS));
    const duration = Math.max(1, Math.round((end.getTime() - start.getTime()) / DAY_IN_MS) || 1);

    return {
      key: (item as any).id as string,
      name: ("name" in item ? item.name : (item as any).title) as string,
      startOffset,
      duration,
      color: getColor(item),
      details: getDetails(item, start, end),
    };
  });

  return { data, minDate, totalDays };
}

function TimelineTooltip({
  active,
  payload,
  minDate,
}: {
  active?: boolean;
  payload?: any[];
  minDate: Date;
}) {
  if (!active || !payload?.length) return null;
  const datum = payload[payload.length - 1]?.payload as ChartDatum | undefined;
  if (!datum) return null;

  const start = addDays(minDate, datum.startOffset);
  const end = addDays(minDate, datum.startOffset + datum.duration);

  return (
    <div className="rounded-md border border-gray-200 bg-white p-3 text-xs shadow-md dark:border-gray-700 dark:bg-gray-900">
      <div className="font-semibold text-gray-900 dark:text-gray-100">{datum.name}</div>
      <div className="mt-1 text-gray-600 dark:text-gray-300">
        {formatDateLong(start)} → {formatDateLong(end)} ({datum.duration} days)
      </div>
      {Object.entries(datum.details)
        .filter(([, value]) => value)
        .map(([key, value]) => (
          <div key={key} className="mt-1 text-gray-500 dark:text-gray-400">
            <span className="font-medium capitalize">{key.replace(/_/g, " ")}:</span>{" "}
            <span>{value}</span>
          </div>
        ))}
    </div>
  );
}

function TimelineContent({
  timeline,
  timelineError,
  activeProjectName,
}: {
  timeline: ProjectTimelineResponse | null;
  timelineError: Error | null;
  activeProjectName: string | null;
}) {
  const [sprintFilter, setSprintFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [assigneeFilter, setAssigneeFilter] = useState<string>("all");

  const scheduledSprints = timeline?.sprints ?? [];
  const scheduledTasks = timeline?.tasks ?? [];
  const unscheduledSprints = timeline?.unscheduled?.sprints ?? [];
  const unscheduledTasks = timeline?.unscheduled?.tasks ?? [];

  const sprintOptions = useMemo(() => {
    const map = new Map<string, string>();
    scheduledTasks.forEach((task) => {
      if (task.sprint_id && task.sprint_name) {
        map.set(task.sprint_id, task.sprint_name);
      }
    });
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }));
  }, [scheduledTasks]);

  const statusOptions = useMemo(() => {
    const map = new Map<string, string>();
    scheduledTasks.forEach((task) => {
      if (!task.status) return;
      const value = task.status.toLowerCase();
      if (!map.has(value)) {
        map.set(value, formatStatusLabel(task.status));
      }
    });
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }));
  }, [scheduledTasks]);

  const assigneeOptions = useMemo(() => {
    const map = new Map<string, string>();
    scheduledTasks.forEach((task) => {
      const key = task.assignee_id ?? (task.assigned_to ? `name:${task.assigned_to}` : UNASSIGNED_KEY);
      const label = task.assigned_to ?? task.assignee_id ?? "Unassigned";
      if (!map.has(key)) {
        map.set(key, label);
      }
    });
    if (!map.has(UNASSIGNED_KEY)) {
      map.set(UNASSIGNED_KEY, "Unassigned");
    }
    return Array.from(map.entries()).map(([value, label]) => ({ value, label }));
  }, [scheduledTasks]);

  const filteredTasks = useMemo(() => {
    return scheduledTasks.filter((task) => {
      if (sprintFilter !== "all" && task.sprint_id !== sprintFilter) return false;
      if (statusFilter !== "all" && (task.status?.toLowerCase() ?? "") !== statusFilter) return false;
      if (assigneeFilter !== "all") {
        if (assigneeFilter === UNASSIGNED_KEY) {
          if (task.assignee_id || task.assigned_to) return false;
        } else if (
          task.assignee_id !== assigneeFilter &&
          `name:${task.assigned_to}` !== assigneeFilter
        ) {
          return false;
        }
      }
      return true;
    });
  }, [scheduledTasks, sprintFilter, statusFilter, assigneeFilter]);

  const sprintChart = useMemo(() => {
    return buildChartData(
      scheduledSprints,
      (sprint) => parseISO(sprint.start_date),
      (sprint) => parseISO(sprint.end_date),
      getSprintColor,
      (sprint, start, end) => ({
        status: formatStatusLabel(sprint.status),
        goal: sprint.goal,
        start_date: formatDateLong(start),
        end_date: formatDateLong(end),
      }),
    );
  }, [scheduledSprints]);

  const taskChart = useMemo(() => {
    return buildChartData(
      filteredTasks,
      (task) => parseISO(task.start_date),
      (task) => parseISO(task.due_date),
      getTaskColor,
      (task, start, end) => ({
        status: formatStatusLabel(task.status),
        sprint: task.sprint_name ?? "—",
        assignee: task.assigned_to ?? "Unassigned",
        start_date: formatDateLong(start),
        due_date: formatDateLong(end),
      }),
    );
  }, [filteredTasks]);

  const unscheduledTaskPreview = unscheduledTasks.slice(0, 6);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Timeline</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {activeProjectName ?? "Selected project"}
          </p>
        </div>
        {timelineError ? (
          <Badge variant="destructive" className="text-xs">
            {timelineError.message}
          </Badge>
        ) : null}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-100 text-blue-600 dark:bg-blue-500/20 dark:text-blue-300">
              <CalendarRange className="h-4 w-4" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                Scheduled sprints
              </p>
              <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {scheduledSprints.length}
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
                Tasks on timeline
              </p>
              <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {scheduledTasks.length}
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
                Unscheduled tasks
              </p>
              <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {unscheduledTasks.length}
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
                Timeline coverage
              </p>
              <p className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {Math.max(sprintChart.totalDays, taskChart.totalDays) || "—"}{" "}
                {Math.max(sprintChart.totalDays, taskChart.totalDays) ? "days" : ""}
              </p>
            </div>
          </div>
        </Card>
      </div>

      {unscheduledSprints.length > 0 || unscheduledTasks.length > 0 ? (
        <Card className="border border-amber-300 bg-amber-50/70 p-5 dark:border-amber-500/40 dark:bg-amber-950/30">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-amber-600 dark:text-amber-400" />
            <div>
              <p className="text-sm font-semibold text-amber-700 dark:text-amber-200">
                Some work items are missing schedule information
              </p>
              <p className="mt-1 text-xs text-amber-700/80 dark:text-amber-200/70">
                Add start and end dates to include them in the Gantt chart.
              </p>

              {unscheduledSprints.length > 0 ? (
                <div className="mt-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-amber-600 dark:text-amber-300">
                    Sprints ({unscheduledSprints.length})
                  </p>
                  <ul className="mt-1 space-y-1 text-sm text-amber-700 dark:text-amber-100">
                    {unscheduledSprints.slice(0, 4).map((sprint) => (
                      <li key={sprint.id}>
                        <span className="font-medium">{sprint.name}</span> — {describeMissing(sprint.missing_reason)}
                      </li>
                    ))}
                    {unscheduledSprints.length > 4 ? (
                      <li className="text-xs text-amber-600/80 dark:text-amber-200/70">
                        + {unscheduledSprints.length - 4} more sprints
                      </li>
                    ) : null}
                  </ul>
                </div>
              ) : null}

              {unscheduledTasks.length > 0 ? (
                <div className="mt-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-amber-600 dark:text-amber-300">
                    Tasks ({unscheduledTasks.length})
                  </p>
                  <ul className="mt-1 space-y-1 text-sm text-amber-700 dark:text-amber-100">
                    {unscheduledTaskPreview.map((task) => (
                      <li key={task.id}>
                        <span className="font-medium">{task.title}</span> — {describeMissing(task.missing_reason)}
                      </li>
                    ))}
                    {unscheduledTasks.length > unscheduledTaskPreview.length ? (
                      <li className="text-xs text-amber-600/80 dark:text-amber-200/70">
                        + {unscheduledTasks.length - unscheduledTaskPreview.length} more tasks
                      </li>
                    ) : null}
                  </ul>
                </div>
              ) : null}
            </div>
          </div>
        </Card>
      ) : null}

      <Card className="space-y-5 p-6">
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

        {sprintChart.data.length === 0 || !sprintChart.minDate ? (
          <div className="rounded border border-dashed border-gray-300 bg-gray-50 py-12 text-center text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-900">
            No sprints have complete scheduling information yet.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={Math.max(280, sprintChart.data.length * 48)}>
            <BarChart
              data={sprintChart.data}
              layout="vertical"
              margin={{ top: 16, right: 24, left: 200, bottom: 16 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                type="number"
                domain={[0, sprintChart.totalDays]}
                tickFormatter={(value) => formatDateShort(addDays(sprintChart.minDate!, Number(value)))}
              />
              <YAxis type="category" dataKey="name" width={200} />
              <Tooltip content={<TimelineTooltip minDate={sprintChart.minDate!} />} />
              <Bar dataKey="startOffset" stackId="sprint" fill="transparent" isAnimationActive={false} />
              <Bar dataKey="duration" stackId="sprint" radius={[0, 4, 4, 0]}>
                {sprintChart.data.map((datum) => (
                  <Cell key={datum.key} fill={datum.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </Card>

      <Card className="space-y-5 p-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Task schedule</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Tasks with start and due dates appear here. Use the filters to focus on specific sprints, statuses, or assignees.
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

        {timelineError ? (
          <div className="rounded border border-rose-200 bg-rose-50 py-10 text-center text-sm text-rose-600 dark:border-rose-500/40 dark:bg-rose-950/30 dark:text-rose-200">
            Failed to load timeline: {timelineError.message}
          </div>
        ) : taskChart.data.length === 0 || !taskChart.minDate ? (
          <div className="rounded border border-dashed border-gray-300 bg-gray-50 py-12 text-center text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-900">
            No tasks match the current filters or have complete scheduling information.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={Math.max(320, taskChart.data.length * 48)}>
            <BarChart
              data={taskChart.data}
              layout="vertical"
              margin={{ top: 16, right: 24, left: 220, bottom: 16 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis
                type="number"
                domain={[0, taskChart.totalDays]}
                tickFormatter={(value) => formatDateShort(addDays(taskChart.minDate!, Number(value)))}
              />
              <YAxis type="category" dataKey="name" width={220} />
              <Tooltip content={<TimelineTooltip minDate={taskChart.minDate!} />} />
              <Bar dataKey="startOffset" stackId="task" fill="transparent" isAnimationActive={false} />
              <Bar dataKey="duration" stackId="task" radius={[0, 4, 4, 0]}>
                {taskChart.data.map((datum) => (
                  <Cell key={datum.key} fill={datum.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </Card>
    </div>
  );
}

export function TimelineView() {
  const { activeProject, projectIdForData, projectsLoading } = useProjectData();
  const {
    timeline,
    loading: timelineLoading,
    error: timelineError,
  } = useTimeline(projectIdForData);

  if (!projectIdForData) {
    return (
      <Card className="p-6 text-center">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Timeline</h2>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Select a project from the header to view its Gantt chart.
        </p>
      </Card>
    );
  }

  const isLoading = projectsLoading || timelineLoading;

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return (
    <TimelineContent
      timeline={timeline}
      timelineError={timelineError}
      activeProjectName={activeProject?.name ?? null}
    />
  );
}

