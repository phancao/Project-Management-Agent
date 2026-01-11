// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";

import { Card } from "~/components/ui/card";
import { WorkspaceLoading } from "~/components/ui/workspace-loading";
import { useCycleTimeChart } from "~/core/api/hooks/pm/use-analytics";
import { useSearchParams } from "next/navigation";

export function CycleTimeView() {
  const searchParams = useSearchParams();
  const projectId = searchParams?.get("project");
  const { data: chartData, isLoading: loading, error } = useCycleTimeChart(projectId, undefined, 60);

  // Transform chart data for Recharts
  const scatterData = chartData?.series[0]?.data.map((point) => ({
    date: new Date(point.date!).getTime(),
    dateLabel: new Date(point.date!).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    cycleTime: point.value,
    title: point.label,
    type: point.metadata?.type || "task",
  })) || [];

  // Percentile lines
  const p50Line = chartData?.series[1]?.data.map((point) => ({
    date: new Date(point.date!).getTime(),
    value: point.value,
  })) || [];

  const p85Line = chartData?.series[2]?.data.map((point) => ({
    date: new Date(point.date!).getTime(),
    value: point.value,
  })) || [];

  const p95Line = chartData?.series[3]?.data.map((point) => ({
    date: new Date(point.date!).getTime(),
    value: point.value,
  })) || [];

  // Combine all data for the chart
  const combinedData = scatterData.map((point, index) => ({
    ...point,
    p50: p50Line[index]?.value,
    p85: p85Line[index]?.value,
    p95: p95Line[index]?.value,
  }));

  // Extract metadata
  const metadata = chartData?.metadata || {};
  const avgCycleTime = metadata.avg_cycle_time ?? 0;
  const medianCycleTime = metadata.median_cycle_time ?? 0;
  const p50 = metadata.percentile_50 ?? 0;
  const p85 = metadata.percentile_85 ?? 0;
  const p95 = metadata.percentile_95 ?? 0;
  const totalItems = metadata.total_items ?? 0;
  const outliers = metadata.outliers || [];
  const insights = metadata.insights || [];

  if (loading) {
    return (
      <WorkspaceLoading
        title="Loading Cycle Time"
        subtitle="Computing percentiles..."
        items={[
          { label: "Cycle Time Data", isLoading: true },
        ]}
      />
    );
  }

  // Cycle Time Description component (reusable)
  const CycleTimeDescription = () => (
    <Card className="p-6 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">📊 Understanding Cycle Time</h3>
      <p className="text-sm text-gray-700 dark:text-gray-300 mb-3">
        Cycle time measures how long work items take from start to completion. Lower and more consistent cycle times indicate better predictability and flow.
      </p>
      <ul className="text-sm text-gray-700 dark:text-gray-300 space-y-1 list-disc list-inside">
        <li><strong>50th Percentile:</strong> Half of items complete faster than this</li>
        <li><strong>85th Percentile:</strong> Use this for realistic commitments</li>
        <li><strong>95th Percentile:</strong> Items above this are outliers - investigate blockers</li>
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
                Unable to Load Cycle Time Chart
              </h3>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                {error.message.includes("503") || error.message.includes("NotImplementedError")
                  ? "Cycle time chart is not available for this project type."
                  : "There was an error loading the cycle time chart. Please try again later."}
              </p>
            </div>
          </div>
        </Card>
        <CycleTimeDescription />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">{chartData?.title || "Cycle Time / Control Chart"}</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Last 60 Days - {totalItems} Completed Items
          </p>
        </div>
        {outliers.length > 0 && (
          <div className="px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">
            ⚠ {outliers.length} Outlier{outliers.length > 1 ? 's' : ''}
          </div>
        )}
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <Card className="p-4">
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Average</div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">{avgCycleTime.toFixed(1)}d</div>
        </Card>
        <Card className="p-4">
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Median</div>
          <div className="text-2xl font-bold text-blue-600">{medianCycleTime.toFixed(1)}d</div>
        </Card>
        <Card className="p-4">
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">50th %ile</div>
          <div className="text-2xl font-bold text-green-600">{p50.toFixed(1)}d</div>
        </Card>
        <Card className="p-4">
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">85th %ile</div>
          <div className="text-2xl font-bold text-orange-600">{p85.toFixed(1)}d</div>
        </Card>
        <Card className="p-4">
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">95th %ile</div>
          <div className="text-2xl font-bold text-red-600">{p95.toFixed(1)}d</div>
        </Card>
      </div>

      {/* Cycle Time Chart */}
      <Card className="p-6">
        <ResponsiveContainer width="100%" height={400}>
          <ScatterChart>
            <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
            <XAxis
              dataKey="date"
              type="number"
              domain={['dataMin', 'dataMax']}
              tickFormatter={(timestamp) => new Date(timestamp).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
              stroke="#666"
            />
            <YAxis
              stroke="#666"
              label={{ value: 'Cycle Time (days)', angle: -90, position: 'insideLeft' }}
            />
            <ZAxis range={[50, 50]} />
            <Tooltip
              contentStyle={{ backgroundColor: 'rgba(255, 255, 255, 0.95)', border: '1px solid #ccc' }}
              formatter={(value: any, name: any) => {
                if (name === 'cycleTime') return [`${value} days`, 'Cycle Time'];
                return [value, name];
              }}
              labelFormatter={(label) => new Date(label).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
            />
            <Legend />

            {/* Percentile Lines */}
            <Line
              data={combinedData}
              type="monotone"
              dataKey="p50"
              stroke="#10b981"
              strokeWidth={2}
              name="50th Percentile"
              dot={false}
            />
            <Line
              data={combinedData}
              type="monotone"
              dataKey="p85"
              stroke="#f59e0b"
              strokeWidth={2}
              name="85th Percentile"
              dot={false}
            />
            <Line
              data={combinedData}
              type="monotone"
              dataKey="p95"
              stroke="#ef4444"
              strokeWidth={2}
              name="95th Percentile"
              dot={false}
            />

            {/* Scatter Points */}
            <Scatter
              data={combinedData}
              fill="#3b82f6"
              name="Cycle Time"
              shape="circle"
            />
          </ScatterChart>
        </ResponsiveContainer>
      </Card>

      {/* Insights & Outliers */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Insights */}
        {insights.length > 0 && (
          <Card className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Insights</h3>
            <div className="space-y-3">
              {insights.map((insight: string, index: number) => (
                <div key={index} className="flex items-start gap-3">
                  <div className="w-2 h-2 rounded-full bg-blue-500 mt-2"></div>
                  <p className="text-sm text-gray-700 dark:text-gray-300">{insight}</p>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Outliers */}
        {outliers.length > 0 && (
          <Card className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Outliers (Above 95th Percentile)</h3>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {outliers.map((outlier: any, index: number) => (
                <div key={index} className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900 dark:text-white">{outlier.title}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">ID: {outlier.id}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-bold text-red-600">{outlier.cycle_time_days}d</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">cycle time</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>

      {/* Explanation */}
      <CycleTimeDescription />
    </div>
  );
}

