// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Card } from "~/components/ui/card";
import { useVelocityChart } from "~/core/api/hooks/pm/use-analytics";
import { useActiveProject } from "~/core/api/hooks/pm/use-projects";

export function VelocityView() {
  const { activeProject } = useActiveProject();
  const { data: chartData, isLoading: loading, error } = useVelocityChart(activeProject?.id || null, 6);

  // Transform chart data for Recharts
  const velocityData = chartData?.series[0]?.data.map((point, index) => {
    const completedPoint = chartData.series[1]?.data[index];
    return {
      sprint: point.label || `Sprint ${index + 1}`,
      committed: point.value,
      completed: completedPoint?.value || 0,
    };
  }) || [];

  // Extract metadata
  const metadata = chartData?.metadata || {};
  const averageVelocity = metadata.average_velocity || 0;
  const medianVelocity = metadata.median_velocity || 0;
  const latestVelocity = metadata.latest_velocity || 0;
  const trend = metadata.trend || "stable";
  const predictabilityScore = metadata.predictability_score || 0;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-gray-500 dark:text-gray-400">Loading velocity chart...</div>
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

  // Trend indicator
  const getTrendColor = () => {
    if (trend === "increasing") return "text-green-600";
    if (trend === "decreasing") return "text-red-600";
    return "text-gray-600";
  };

  const getTrendIcon = () => {
    if (trend === "increasing") return "↗";
    if (trend === "decreasing") return "↘";
    return "→";
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">{chartData?.title || "Team Velocity"}</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {activeProject?.name || "Project"} - Last {velocityData.length} Sprints
          </p>
        </div>
        <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium ${getTrendColor()} bg-gray-100 dark:bg-gray-800`}>
          <span className="text-xl">{getTrendIcon()}</span>
          <span className="capitalize">{trend}</span>
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Average Velocity</div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">{averageVelocity.toFixed(1)} pts</div>
        </Card>
        <Card className="p-4">
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Median Velocity</div>
          <div className="text-2xl font-bold text-blue-600">{medianVelocity.toFixed(1)} pts</div>
        </Card>
        <Card className="p-4">
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Latest Sprint</div>
          <div className="text-2xl font-bold text-green-600">{latestVelocity.toFixed(1)} pts</div>
        </Card>
        <Card className="p-4">
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Predictability</div>
          <div className="text-2xl font-bold text-purple-600">
            {(predictabilityScore * 100).toFixed(0)}%
          </div>
        </Card>
      </div>

      {/* Velocity Chart */}
      <Card className="p-6">
        <ResponsiveContainer width="100%" height={400}>
          <BarChart data={velocityData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
            <XAxis dataKey="sprint" stroke="#666" />
            <YAxis stroke="#666" label={{ value: 'Story Points', angle: -90, position: 'insideLeft' }} />
            <Tooltip 
              contentStyle={{ backgroundColor: 'rgba(255, 255, 255, 0.95)', border: '1px solid #ccc' }}
              formatter={(value: number) => `${value.toFixed(1)} pts`}
            />
            <Legend />
            <Bar 
              dataKey="committed" 
              fill="#94a3b8" 
              name="Committed"
              radius={[4, 4, 0, 0]}
            />
            <Bar 
              dataKey="completed" 
              fill="#10b981" 
              name="Completed"
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </Card>

      {/* Insights */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Insights</h3>
        <div className="space-y-3">
          <div className="flex items-start gap-3">
            <div className="w-2 h-2 rounded-full bg-blue-500 mt-2"></div>
            <div>
              <p className="text-sm text-gray-700 dark:text-gray-300">
                <span className="font-semibold">Average velocity:</span> {averageVelocity.toFixed(1)} story points per sprint
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="w-2 h-2 rounded-full bg-green-500 mt-2"></div>
            <div>
              <p className="text-sm text-gray-700 dark:text-gray-300">
                <span className="font-semibold">Predictability score:</span> {(predictabilityScore * 100).toFixed(0)}% 
                {predictabilityScore >= 0.8 ? " (Excellent)" : predictabilityScore >= 0.6 ? " (Good)" : " (Needs Improvement)"}
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className={`w-2 h-2 rounded-full mt-2 ${trend === "increasing" ? "bg-green-500" : trend === "decreasing" ? "bg-red-500" : "bg-gray-500"}`}></div>
            <div>
              <p className="text-sm text-gray-700 dark:text-gray-300">
                <span className="font-semibold">Trend:</span> Team velocity is <span className="capitalize">{trend}</span>
                {trend === "increasing" && " - Great job! 🎉"}
                {trend === "decreasing" && " - Consider reviewing team capacity and blockers"}
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="w-2 h-2 rounded-full bg-purple-500 mt-2"></div>
            <div>
              <p className="text-sm text-gray-700 dark:text-gray-300">
                <span className="font-semibold">Recommendation:</span> For next sprint, consider committing to ~{averageVelocity.toFixed(0)} story points based on historical average
              </p>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}

