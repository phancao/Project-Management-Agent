// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Card } from "~/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "~/components/ui/select";
import { useBurndownChart } from "~/core/api/hooks/pm/use-analytics";
import { useSprints } from "~/core/api/hooks/pm/use-sprints";

export function BurndownView() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  
  const projectId = searchParams?.get("project");
  const sprintParam = searchParams?.get("sprint");

  const {
    sprints,
    loading: sprintsLoading,
    error: sprintsError,
  } = useSprints(projectId ?? "");

  const sortedSprints = useMemo(() => {
    if (!sprints) return [];

    const normalizeStatus = (status?: string) => (status ?? "").toLowerCase();
    const statusPriority = (status?: string) => {
      const value = normalizeStatus(status);
      if (["active", "in_progress", "ongoing"].includes(value)) return 0;
      if (["future", "planned", "planning"].includes(value)) return 1;
      return 2; // completed/closed or unknown
    };

    const dateValue = (value?: string) => {
      if (!value) return Number.MIN_SAFE_INTEGER;
      const time = new Date(value).getTime();
      return Number.isNaN(time) ? Number.MIN_SAFE_INTEGER : time;
    };

    return [...sprints].sort((a, b) => {
      const statusDiff = statusPriority(a.status) - statusPriority(b.status);
      if (statusDiff !== 0) return statusDiff;

      const aDate = Math.max(dateValue(a.start_date), dateValue(a.end_date));
      const bDate = Math.max(dateValue(b.start_date), dateValue(b.end_date));

      return bDate - aDate; // Newest first within the same status bucket
    });
  }, [sprints]);

  const [selectedSprintId, setSelectedSprintId] = useState<string | null>(null);

  useEffect(() => {
    if (!sortedSprints.length) {
      setSelectedSprintId(null);
      return;
    }

    setSelectedSprintId((current) => {
      if (current && sortedSprints.some((s) => s.id === current)) {
        return current;
      }
      if (sprintParam && sortedSprints.some((s) => s.id === sprintParam)) {
        return sprintParam;
      }
      return sortedSprints[0]?.id ?? "";
    });
  }, [sortedSprints, sprintParam]);

  const { data: chartData, isLoading: loading, error } = useBurndownChart(projectId, selectedSprintId ?? undefined);

  const handleSprintChange = (value: string) => {
    setSelectedSprintId(value);
    if (!searchParams) return;

    const params = new URLSearchParams(searchParams.toString());
    params.set("sprint", value);
    if (projectId) {
      params.set("project", projectId);
    }
    router.replace(`${pathname}?${params.toString()}`);
  };

  // Transform chart data for Recharts
  const burndownData = chartData?.series[0]?.data.map((point, index) => {
    const actualPoint = chartData.series[1]?.data[index];
    return {
      day: point.label || new Date(point.date!).toLocaleDateString(),
      ideal: point.value,
      actual: actualPoint?.value ?? 0,
    };
  }) || [];

  // Extract metadata
  const metadata = chartData?.metadata || {};
  const totalScope = metadata.total_scope ?? 0;
  const remaining = metadata.remaining ?? 0;
  const completed = metadata.completed ?? 0;
  const completionPercentage = metadata.completion_percentage ?? 0;
  const onTrack = metadata.on_track || false;

  if (sprintsError) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-red-500">Failed to load sprints: {sprintsError.message}</div>
      </div>
    );
  }

  if (!projectId) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-gray-500 dark:text-gray-400">Select a project to view burndown chart.</div>
      </div>
    );
  }

  if (sprintsLoading || (!selectedSprintId && sortedSprints.length > 0)) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-gray-500 dark:text-gray-400">Loading sprints...</div>
      </div>
    );
  }

  if (!sortedSprints.length) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-gray-500 dark:text-gray-400">
          No sprints found for this project. Create or activate a sprint to view the burndown chart.
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-gray-500 dark:text-gray-400">Loading burndown...</div>
      </div>
    );
  }

  // Burndown Description component (reusable)
  const BurndownDescription = () => (
    <Card className="p-6 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">📊 What is a Burndown Chart?</h3>
      <p className="text-sm text-gray-700 dark:text-gray-300">
        A burndown chart tracks the amount of work remaining in a sprint over time. The <strong>ideal line</strong> shows the expected 
        progress if work is completed at a steady pace, while the <strong>actual line</strong> shows real progress. Use this chart to:
      </p>
      <ul className="text-sm text-gray-700 dark:text-gray-300 mt-2 space-y-1 list-disc list-inside">
        <li>Monitor if the team is on track to complete the sprint goal</li>
        <li>Identify if the team is ahead or behind schedule</li>
        <li>Spot scope changes (when the actual line goes up)</li>
        <li>Forecast sprint completion based on current velocity</li>
      </ul>
    </Card>
  );

  if (error) {
    return (
      <div className="space-y-6">
        <Card className="p-6 text-center">
          <div className="mx-auto max-w-md space-y-4">
            <div className="flex justify-center">
              <div className="rounded-full bg-red-100 p-3 dark:bg-red-900/30">
                <span className="text-2xl">📊</span>
              </div>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Unable to Load Burndown Chart
              </h3>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                {error.message.includes("503") || error.message.includes("NotImplementedError") 
                  ? "Burndown chart is not available for this project type."
                  : "There was an error loading the burndown chart. Please try again later."}
              </p>
            </div>
          </div>
        </Card>
        <BurndownDescription />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">{chartData?.title || "Burndown Chart"}</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Sprint Progress
          </p>
        </div>
        <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:gap-4">
          <Select value={selectedSprintId ?? undefined} onValueChange={handleSprintChange}>
            <SelectTrigger className="min-w-[20rem] max-w-full pr-10 text-left">
              <SelectValue placeholder="Select sprint" className="truncate" />
            </SelectTrigger>
            <SelectContent className="min-w-[20rem] max-w-xl">
              {sortedSprints.map((sprint) => {
                const normalizedStatus = (sprint.status ?? "").toLowerCase();
                const statusLabel =
                  normalizedStatus === "active"
                    ? "Active"
                    : normalizedStatus === "future"
                    ? "Planned"
                    : normalizedStatus === "planning"
                    ? "Planning"
                    : normalizedStatus === "closed" || normalizedStatus === "completed"
                    ? "Completed"
                    : sprint.status || "Unknown";

                return (
                  <SelectItem key={sprint.id} value={sprint.id}>
                    <div className="flex flex-col gap-0.5">
                      <span className="font-medium truncate">{sprint.name}</span>
                      <span className="text-xs text-muted-foreground truncate">
                        {statusLabel}
                        {sprint.start_date
                          ? ` • ${new Date(sprint.start_date).toLocaleDateString()}`
                          : ""}
                      </span>
                    </div>
                  </SelectItem>
                );
              })}
            </SelectContent>
          </Select>

          {onTrack !== undefined && (
            <div className={`px-3 py-1 rounded-full text-sm font-medium ${onTrack ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'}`}>
              {onTrack ? '✓ On Track' : '⚠ Behind Schedule'}
            </div>
          )}
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Total Scope</div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">{totalScope.toFixed(1)} pts</div>
        </Card>
        <Card className="p-4">
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Completed</div>
          <div className="text-2xl font-bold text-green-600">{completed.toFixed(1)} pts</div>
        </Card>
        <Card className="p-4">
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Remaining</div>
          <div className="text-2xl font-bold text-orange-600">{remaining.toFixed(1)} pts</div>
        </Card>
        <Card className="p-4">
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Progress</div>
          <div className="text-2xl font-bold text-blue-600">
            {completionPercentage.toFixed(0)}%
          </div>
        </Card>
      </div>

      {/* Burndown Chart */}
      <Card className="p-6">
        <ResponsiveContainer width="100%" height={400}>
          <AreaChart data={burndownData}>
            <defs>
              <linearGradient id="colorIdeal" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#8884d8" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#8884d8" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="colorActual" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#82ca9d" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#82ca9d" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
            <XAxis dataKey="day" stroke="#666" />
            <YAxis stroke="#666" />
            <Tooltip 
              contentStyle={{ backgroundColor: 'rgba(255, 255, 255, 0.95)', border: '1px solid #ccc' }}
              formatter={(value: number) => `${value.toFixed(1)}h`}
            />
            <Legend />
            <Area 
              type="monotone" 
              dataKey="ideal" 
              stroke="#8884d8" 
              fillOpacity={1}
              fill="url(#colorIdeal)"
              name="Ideal Burndown"
              strokeWidth={2}
            />
            <Area 
              type="monotone" 
              dataKey="actual" 
              stroke="#82ca9d" 
              fillOpacity={1}
              fill="url(#colorActual)"
              name="Actual Burndown"
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </Card>

      {/* Scope Changes */}
      {metadata.scope_changes && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Scope Changes</h3>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <div className="text-sm text-gray-500 dark:text-gray-400 mb-2">Added</div>
              <div className="text-3xl font-bold text-blue-600">
                +{metadata.scope_changes.added ?? 0}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-500 dark:text-gray-400 mb-2">Removed</div>
              <div className="text-3xl font-bold text-red-600">
                -{metadata.scope_changes.removed ?? 0}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-500 dark:text-gray-400 mb-2">Net Change</div>
              <div className={`text-3xl font-bold ${(metadata.scope_changes.net ?? 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {(metadata.scope_changes.net ?? 0) >= 0 ? '+' : ''}{metadata.scope_changes.net ?? 0}
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Explanation */}
      <BurndownDescription />
    </div>
  );
}

