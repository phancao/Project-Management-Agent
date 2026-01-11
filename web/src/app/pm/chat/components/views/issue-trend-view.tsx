// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Card } from "~/components/ui/card";
import { WorkspaceLoading } from "~/components/ui/workspace-loading";
import { useIssueTrendChart } from "~/core/api/hooks/pm/use-analytics";
import { useSearchParams } from "next/navigation";

export function IssueTrendView() {
  const searchParams = useSearchParams();
  const projectId = searchParams?.get("project");
  const { data: chartData, isLoading: loading, error } = useIssueTrendChart(projectId, 30);

  // Transform chart data for Recharts
  const trendData = chartData?.series[0]?.data.map((point, index) => ({
    date: point.label || new Date(point.date!).toLocaleDateString(),
    created: chartData.series[0]?.data[index]?.value ?? 0,
    resolved: chartData.series[1]?.data[index]?.value ?? 0,
    netChange: chartData.series[2]?.data[index]?.value ?? 0,
    cumulativeNet: chartData.series[3]?.data[index]?.value ?? 0,
  })) || [];

  const metadata = chartData?.metadata || {};
  const totalCreated = metadata.total_created ?? 0;
  const totalResolved = metadata.total_resolved ?? 0;
  const netChange = metadata.net_change ?? 0;
  const avgCreatedPerDay = metadata.avg_created_per_day ?? 0;
  const avgResolvedPerDay = metadata.avg_resolved_per_day ?? 0;
  const cumulativeNet = metadata.cumulative_net ?? 0;
  const insights = metadata.insights || [];

  if (loading) {
    return (
      <WorkspaceLoading
        title="Loading Issue Trend"
        subtitle="Analyzing trends..."
        items={[
          { label: "Trend Data", isLoading: true },
        ]}
      />
    );
  }

  // Issue Trend Description component (reusable)
  const IssueTrendDescription = () => (
    <Card className="p-6 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">📈 What is Issue Trend Analysis?</h3>
      <p className="text-sm text-gray-700 dark:text-gray-300">
        Issue trend analysis tracks how issues are created and resolved over time. It helps you understand if your backlog
        is growing or shrinking. Use this chart to:
      </p>
      <ul className="text-sm text-gray-700 dark:text-gray-300 mt-2 space-y-1 list-disc list-inside">
        <li><strong>Monitor backlog health:</strong> Is work being resolved faster than it's created?</li>
        <li><strong>Identify capacity issues:</strong> If created &gt; resolved consistently, you may need more resources</li>
        <li><strong>Track team productivity:</strong> See resolution rates and trends over time</li>
        <li><strong>Plan capacity:</strong> Use historical data to forecast future needs</li>
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
                <span className="text-2xl">📈</span>
              </div>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Unable to Load Issue Trend Chart
              </h3>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                {error.message.includes("503") || error.message.includes("NotImplementedError")
                  ? "Issue trend chart is not available for this project type."
                  : "There was an error loading the issue trend chart. Please try again later."}
              </p>
            </div>
          </div>
        </Card>
        <IssueTrendDescription />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">{chartData?.title || "Issue Trend Analysis"}</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Last 30 Days
          </p>
        </div>
        {netChange !== 0 && (
          <div className={`px-3 py-1 rounded-full text-sm font-medium ${netChange > 0
            ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
            : "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
            }`}>
            {netChange > 0 ? "⚠️" : "✅"} {netChange > 0 ? "+" : ""}{netChange} Net Change
          </div>
        )}
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <Card className="p-4 border-indigo-500/20 dark:border-indigo-500/30 shadow-lg shadow-indigo-500/10 dark:shadow-indigo-500/15 ring-1 ring-indigo-500/10 dark:ring-indigo-500/15">
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Total Created</div>
          <div className="text-2xl font-bold text-blue-600">{totalCreated}</div>
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {avgCreatedPerDay.toFixed(1)}/day
          </div>
        </Card>
        <Card className="p-4 border-indigo-500/20 dark:border-indigo-500/30 shadow-lg shadow-indigo-500/10 dark:shadow-indigo-500/15 ring-1 ring-indigo-500/10 dark:ring-indigo-500/15">
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Total Resolved</div>
          <div className="text-2xl font-bold text-green-600">{totalResolved}</div>
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {avgResolvedPerDay.toFixed(1)}/day
          </div>
        </Card>
        <Card className="p-4 border-indigo-500/20 dark:border-indigo-500/30 shadow-lg shadow-indigo-500/10 dark:shadow-indigo-500/15 ring-1 ring-indigo-500/10 dark:ring-indigo-500/15">
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Net Change</div>
          <div className={`text-2xl font-bold ${netChange > 0 ? "text-red-600" : netChange < 0 ? "text-green-600" : "text-gray-600"}`}>
            {netChange > 0 ? "+" : ""}{netChange}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {netChange > 0 ? "Backlog growing" : netChange < 0 ? "Backlog shrinking" : "Stable"}
          </div>
        </Card>
        <Card className="p-4 border-indigo-500/20 dark:border-indigo-500/30 shadow-lg shadow-indigo-500/10 dark:shadow-indigo-500/15 ring-1 ring-indigo-500/10 dark:ring-indigo-500/15">
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Cumulative Net</div>
          <div className={`text-2xl font-bold ${cumulativeNet > 0 ? "text-red-600" : cumulativeNet < 0 ? "text-green-600" : "text-gray-600"}`}>
            {cumulativeNet > 0 ? "+" : ""}{cumulativeNet}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Total impact
          </div>
        </Card>
        <Card className="p-4 border-indigo-500/20 dark:border-indigo-500/30 shadow-lg shadow-indigo-500/10 dark:shadow-indigo-500/15 ring-1 ring-indigo-500/10 dark:ring-indigo-500/15">
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Resolution Rate</div>
          <div className="text-2xl font-bold text-purple-600">
            {totalCreated + totalResolved > 0
              ? ((totalResolved / (totalCreated + totalResolved)) * 100).toFixed(0)
              : 0}%
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Of all activity
          </div>
        </Card>
      </div>

      {/* Trend Chart */}
      <Card className="p-6 border-indigo-500/20 dark:border-indigo-500/30 shadow-lg shadow-indigo-500/10 dark:shadow-indigo-500/20 ring-1 ring-indigo-500/10 dark:ring-indigo-500/15">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Issue Trend Over Time</h3>
        <ResponsiveContainer width="100%" height={400}>
          <ComposedChart data={trendData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
            <XAxis dataKey="date" stroke="#666" />
            <YAxis stroke="#666" />
            <Tooltip
              contentStyle={{ backgroundColor: 'rgba(255, 255, 255, 0.95)', border: '1px solid #ccc' }}
            />
            <Legend />

            {/* Lines for created and resolved */}
            <Line
              type="monotone"
              dataKey="created"
              stroke="#3b82f6"
              strokeWidth={2}
              name="Created"
              dot={{ r: 3 }}
            />
            <Line
              type="monotone"
              dataKey="resolved"
              stroke="#10b981"
              strokeWidth={2}
              name="Resolved"
              dot={{ r: 3 }}
            />

            {/* Bar for net change */}
            <Bar
              dataKey="netChange"
              fill="#f59e0b"
              name="Net Change"
              opacity={0.6}
            />

            {/* Line for cumulative */}
            <Line
              type="monotone"
              dataKey="cumulativeNet"
              stroke="#ef4444"
              strokeWidth={2}
              strokeDasharray="5 5"
              name="Cumulative Net"
              dot={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </Card>

      {/* Insights */}
      {insights.length > 0 && (
        <Card className="p-6 border-indigo-500/20 dark:border-indigo-500/30 shadow-lg shadow-indigo-500/10 dark:shadow-indigo-500/20 ring-1 ring-indigo-500/10 dark:ring-indigo-500/15">
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

      {/* Explanation */}
      <IssueTrendDescription />
    </div>
  );
}

