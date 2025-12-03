// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { useState } from "react";
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { Card } from "~/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "~/components/ui/tabs";
import { useWorkDistributionChart } from "~/core/api/hooks/pm/use-analytics";
import { useSearchParams } from "next/navigation";

type Dimension = "assignee" | "priority" | "type" | "status";

export function WorkDistributionView() {
  const searchParams = useSearchParams();
  const projectId = searchParams?.get("project");
  const [activeDimension, setActiveDimension] = useState<Dimension>("assignee");
  
  const { data: chartData, isLoading: loading, error } = useWorkDistributionChart(projectId, activeDimension);

  const distributionData = chartData?.series[0]?.data.map((point) => ({
    name: point.label || "Unknown",
    value: point.value,
    storyPoints: point.metadata?.story_points ?? 0,
    percentage: point.metadata?.percentage ?? 0,
    pointsPercentage: point.metadata?.points_percentage ?? 0,
    completed: point.metadata?.completed ?? 0,
    inProgress: point.metadata?.in_progress ?? 0,
    todo: point.metadata?.todo ?? 0,
    color: point.metadata?.color || "#3b82f6",
  })) || [];

  const metadata = chartData?.metadata || {};
  const totalItems = metadata.total_items ?? 0;
  const totalPoints = metadata.total_story_points ?? 0;
  const insights = metadata.insights || [];

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-gray-500 dark:text-gray-400">Loading work distribution...</div>
      </div>
    );
  }

  // Work Distribution Description component (reusable)
  const WorkDistributionDescription = () => (
    <Card className="p-6 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">📊 What is Work Distribution?</h3>
      <p className="text-sm text-gray-700 dark:text-gray-300">
        Work distribution charts show how work is spread across different dimensions. Use these charts to:
      </p>
      <ul className="text-sm text-gray-700 dark:text-gray-300 mt-2 space-y-1 list-disc list-inside">
        <li><strong>By Assignee:</strong> Identify workload imbalances and ensure fair distribution</li>
        <li><strong>By Priority:</strong> Understand priority mix and ensure high-priority work is addressed</li>
        <li><strong>By Type:</strong> Track the ratio of stories, bugs, tasks, and features</li>
        <li><strong>By Status:</strong> See how work is distributed across workflow stages</li>
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
                Unable to Load Work Distribution Chart
              </h3>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                {error.message.includes("503") || error.message.includes("NotImplementedError") 
                  ? "Work distribution chart is not available for this project type."
                  : "There was an error loading the work distribution chart. Please try again later."}
              </p>
            </div>
          </div>
        </Card>
        <WorkDistributionDescription />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">{chartData?.title || "Work Distribution"}</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {totalItems} items • {totalPoints} story points
          </p>
        </div>
      </div>

      {/* Dimension Tabs */}
      <Tabs value={activeDimension} onValueChange={(v) => setActiveDimension(v as Dimension)}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="assignee">👤 By Assignee</TabsTrigger>
          <TabsTrigger value="priority">🎯 By Priority</TabsTrigger>
          <TabsTrigger value="type">📋 By Type</TabsTrigger>
          <TabsTrigger value="status">📊 By Status</TabsTrigger>
        </TabsList>

        <TabsContent value={activeDimension} className="space-y-6 mt-6">
          {/* Pie Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* By Count */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Distribution by Count</h3>
              <ResponsiveContainer width="100%" height={400}>
                <PieChart>
                  <Pie
                    data={distributionData}
                    cx="50%"
                    cy="45%"
                    labelLine={false}
                    label={false}
                    outerRadius={120}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {distributionData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ backgroundColor: 'rgba(255, 255, 255, 0.95)', border: '1px solid #ccc' }}
                    formatter={(value: number, name: string, props: any) => [
                      `${value} items (${props.payload.percentage}%)`,
                      props.payload.name
                    ]}
                  />
                  <Legend 
                    verticalAlign="bottom" 
                    height={100}
                    iconType="circle"
                    wrapperStyle={{ paddingTop: '30px' }}
                    formatter={(value, entry: any) => `${value} (${entry.payload.percentage?.toFixed(1) || 0}%)`}
                  />
                </PieChart>
              </ResponsiveContainer>
            </Card>

            {/* By Story Points */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Distribution by Story Points</h3>
              <ResponsiveContainer width="100%" height={400}>
                <PieChart>
                  <Pie
                    data={distributionData}
                    cx="50%"
                    cy="45%"
                    labelLine={false}
                    label={false}
                    outerRadius={120}
                    fill="#8884d8"
                    dataKey="storyPoints"
                  >
                    {distributionData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ backgroundColor: 'rgba(255, 255, 255, 0.95)', border: '1px solid #ccc' }}
                    formatter={(value: number, name: string, props: any) => [
                      `${value} points (${props.payload.pointsPercentage}%)`,
                      props.payload.name
                    ]}
                  />
                  <Legend 
                    verticalAlign="bottom" 
                    height={100}
                    iconType="circle"
                    wrapperStyle={{ paddingTop: '30px' }}
                    formatter={(value, entry: any) => `${value} (${entry.payload.pointsPercentage?.toFixed(1) || 0}%)`}
                  />
                </PieChart>
              </ResponsiveContainer>
            </Card>
          </div>

          {/* Detailed Breakdown Table */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Detailed Breakdown</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-b border-gray-200 dark:border-gray-700">
                  <tr className="text-left">
                    <th className="pb-3 font-semibold text-gray-900 dark:text-white">Name</th>
                    <th className="pb-3 font-semibold text-gray-900 dark:text-white text-right">Items</th>
                    <th className="pb-3 font-semibold text-gray-900 dark:text-white text-right">Story Points</th>
                    <th className="pb-3 font-semibold text-gray-900 dark:text-white text-right">To Do</th>
                    <th className="pb-3 font-semibold text-gray-900 dark:text-white text-right">In Progress</th>
                    <th className="pb-3 font-semibold text-gray-900 dark:text-white text-right">Done</th>
                  </tr>
                </thead>
                <tbody>
                  {distributionData.map((item, index) => (
                    <tr key={index} className="border-b border-gray-100 dark:border-gray-800">
                      <td className="py-3">
                        <div className="flex items-center gap-2">
                          <div 
                            className="w-3 h-3 rounded-full" 
                            style={{ backgroundColor: item.color }}
                          ></div>
                          <span className="font-medium text-gray-900 dark:text-white">{item.name}</span>
                        </div>
                      </td>
                      <td className="py-3 text-right text-gray-700 dark:text-gray-300">
                        {item.value} <span className="text-xs text-gray-500">({item.percentage}%)</span>
                      </td>
                      <td className="py-3 text-right text-gray-700 dark:text-gray-300">
                        {item.storyPoints} <span className="text-xs text-gray-500">({item.pointsPercentage}%)</span>
                      </td>
                      <td className="py-3 text-right text-gray-700 dark:text-gray-300">{item.todo}</td>
                      <td className="py-3 text-right text-blue-600 dark:text-blue-400">{item.inProgress}</td>
                      <td className="py-3 text-right text-green-600 dark:text-green-400">{item.completed}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

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
        </TabsContent>
      </Tabs>

      {/* Explanation */}
      <WorkDistributionDescription />
    </div>
  );
}

