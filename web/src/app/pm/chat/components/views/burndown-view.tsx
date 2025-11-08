// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Card } from "~/components/ui/card";
import { useBurndownChart } from "~/core/api/hooks/pm/use-analytics";
import { useProjects } from "~/core/api/hooks/pm/use-projects";
import { useSearchParams } from "next/navigation";

export function BurndownView() {
  const searchParams = useSearchParams();
  const projectId = searchParams?.get("project");
  const { data: chartData, isLoading: loading, error } = useBurndownChart(projectId);

  // Transform chart data for Recharts
  const burndownData = chartData?.series[0]?.data.map((point, index) => {
    const actualPoint = chartData.series[1]?.data[index];
    return {
      day: point.label || new Date(point.date!).toLocaleDateString(),
      ideal: point.value,
      actual: actualPoint?.value || 0,
    };
  }) || [];

  // Extract metadata
  const metadata = chartData?.metadata || {};
  const totalScope = metadata.total_scope || 0;
  const remaining = metadata.remaining || 0;
  const completed = metadata.completed || 0;
  const completionPercentage = metadata.completion_percentage || 0;
  const onTrack = metadata.on_track || false;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-gray-500 dark:text-gray-400">Loading burndown...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-red-500">Error loading data: {error.message}</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">{chartData?.title || "Burndown Chart"}</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Sprint Progress
          </p>
        </div>
        {onTrack !== undefined && (
          <div className={`px-3 py-1 rounded-full text-sm font-medium ${onTrack ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'}`}>
            {onTrack ? '✓ On Track' : '⚠ Behind Schedule'}
          </div>
        )}
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
                +{metadata.scope_changes.added || 0}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-500 dark:text-gray-400 mb-2">Removed</div>
              <div className="text-3xl font-bold text-red-600">
                -{metadata.scope_changes.removed || 0}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-500 dark:text-gray-400 mb-2">Net Change</div>
              <div className={`text-3xl font-bold ${(metadata.scope_changes.net || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {(metadata.scope_changes.net || 0) >= 0 ? '+' : ''}{metadata.scope_changes.net || 0}
              </div>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}

