// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Card } from "~/components/ui/card";
import { useCFDChart } from "~/core/api/hooks/pm/use-analytics";
import { useSearchParams } from "next/navigation";

export function CFDView() {
  const searchParams = useSearchParams();
  const projectId = searchParams?.get("project");
  const { data: chartData, isLoading: loading, error } = useCFDChart(projectId, undefined, 30);

  // Transform chart data for Recharts (stacked area chart)
  const cfdData = chartData?.series[0]?.data.map((point, index) => {
    const dataPoint: any = {
      date: point.label || new Date(point.date!).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    };
    
    // Add each series data
    chartData?.series.forEach((series) => {
      if (series.data && series.data[index]) {
        dataPoint[series.name] = series.data[index]?.value;
      }
    });

    return dataPoint;
  }) || [];

  // Extract metadata
  const metadata = chartData?.metadata || {};
  const totalItems = metadata.total_items ?? 0;
  const avgWIP = metadata.avg_wip ?? 0;
  const avgCycleTime = metadata.avg_cycle_time_days ?? 0;
  const bottlenecks = metadata.bottlenecks || [];
  const flowEfficiency = metadata.flow_efficiency ?? 0;
  const statusDistribution = metadata.status_distribution || {};

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-gray-500 dark:text-gray-400">Loading CFD...</div>
      </div>
    );
  }

  // CFD Description component (reusable)
  const CFDDescription = () => (
    <Card className="p-6 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">📈 What is a Cumulative Flow Diagram (CFD)?</h3>
      <p className="text-sm text-gray-700 dark:text-gray-300">
        A CFD shows the cumulative count of work items in each status over time. Each colored band represents a workflow stage, 
        and the width of the band shows how many items are in that stage. Use this chart to:
      </p>
      <ul className="text-sm text-gray-700 dark:text-gray-300 mt-2 space-y-1 list-disc list-inside">
        <li>Visualize work flow and identify bottlenecks (wide bands = too much WIP)</li>
        <li>Monitor Work In Progress (WIP) limits and flow efficiency</li>
        <li>Spot when work is piling up in certain stages</li>
        <li>Predict delivery times based on historical flow rates</li>
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
                Unable to Load CFD Chart
              </h3>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                {error.message.includes("503") || error.message.includes("NotImplementedError") 
                  ? "CFD chart is not available for this project type."
                  : "There was an error loading the Cumulative Flow Diagram. Please try again later."}
              </p>
            </div>
          </div>
        </Card>
        <CFDDescription />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">{chartData?.title || "Cumulative Flow Diagram"}</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Last 30 Days
          </p>
        </div>
        {bottlenecks.length > 0 && (
          <div className="px-3 py-1 rounded-full text-sm font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
            ⚠ {bottlenecks.length} Bottleneck{bottlenecks.length > 1 ? 's' : ''}
          </div>
        )}
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Total Items</div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">{totalItems}</div>
        </Card>
        <Card className="p-4">
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Avg WIP</div>
          <div className="text-2xl font-bold text-orange-600">{avgWIP.toFixed(1)}</div>
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">Work in Progress</div>
        </Card>
        <Card className="p-4">
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Avg Cycle Time</div>
          <div className="text-2xl font-bold text-blue-600">{avgCycleTime.toFixed(1)} days</div>
        </Card>
        <Card className="p-4">
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Flow Efficiency</div>
          <div className="text-2xl font-bold text-green-600">{flowEfficiency.toFixed(0)}%</div>
        </Card>
      </div>

      {/* CFD Chart */}
      <Card className="p-6">
        <ResponsiveContainer width="100%" height={400}>
          <AreaChart data={cfdData}>
            <defs>
              {chartData?.series.map((series, index) => (
                <linearGradient key={index} id={`color${series.name.replace(/\s/g, '')}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={series.color || "#8884d8"} stopOpacity={0.8}/>
                  <stop offset="95%" stopColor={series.color || "#8884d8"} stopOpacity={0.3}/>
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
            <XAxis dataKey="date" stroke="#666" />
            <YAxis stroke="#666" label={{ value: 'Cumulative Items', angle: -90, position: 'insideLeft' }} />
            <Tooltip 
              contentStyle={{ backgroundColor: 'rgba(255, 255, 255, 0.95)', border: '1px solid #ccc' }}
              formatter={(value: number) => value.toFixed(0)}
            />
            <Legend />
            {chartData?.series.map((series, index) => (
              <Area
                key={index}
                type="monotone"
                dataKey={series.name}
                stackId="1"
                stroke={series.color || "#8884d8"}
                fill={`url(#color${series.name.replace(/\s/g, '')})`}
                name={series.name}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </Card>

      {/* Status Distribution & Bottlenecks */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Status Distribution */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Current Distribution</h3>
          <div className="space-y-3">
            {Object.entries(statusDistribution).map(([status, count]) => {
              const countNum = count as number;
              const percentage = totalItems > 0 ? (countNum / totalItems * 100) : 0;
              const colors: Record<string, string> = {
                "Done": "bg-green-500",
                "In Review": "bg-blue-500",
                "In Progress": "bg-orange-500",
                "To Do": "bg-gray-400"
              };
              
              return (
                <div key={status}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-700 dark:text-gray-300">{status}</span>
                    <span className="font-semibold text-gray-900 dark:text-white">{countNum} ({percentage.toFixed(0)}%)</span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div 
                      className={`h-2 rounded-full ${colors[status] || 'bg-gray-500'}`}
                      style={{ width: `${percentage}%` }}
                    ></div>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>

        {/* Bottlenecks & Insights */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Insights</h3>
          <div className="space-y-3">
            {bottlenecks.length > 0 ? (
              <>
                <div className="flex items-start gap-3">
                  <div className="w-2 h-2 rounded-full bg-yellow-500 mt-2"></div>
                  <div>
                    <p className="text-sm text-gray-700 dark:text-gray-300">
                      <span className="font-semibold">Bottlenecks detected:</span> {bottlenecks.join(", ")}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      Consider reviewing capacity and removing blockers in these stages
                    </p>
                  </div>
                </div>
              </>
            ) : (
              <div className="flex items-start gap-3">
                <div className="w-2 h-2 rounded-full bg-green-500 mt-2"></div>
                <div>
                  <p className="text-sm text-gray-700 dark:text-gray-300">
                    <span className="font-semibold">No bottlenecks detected</span> - Flow is healthy! ✨
                  </p>
                </div>
              </div>
            )}
            
            <div className="flex items-start gap-3">
              <div className="w-2 h-2 rounded-full bg-blue-500 mt-2"></div>
              <div>
                <p className="text-sm text-gray-700 dark:text-gray-300">
                  <span className="font-semibold">Average WIP:</span> {avgWIP.toFixed(1)} items
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  {avgWIP > 15 ? "Consider limiting WIP to improve focus and flow" : "WIP is at a healthy level"}
                </p>
              </div>
            </div>
            
            <div className="flex items-start gap-3">
              <div className="w-2 h-2 rounded-full bg-purple-500 mt-2"></div>
              <div>
                <p className="text-sm text-gray-700 dark:text-gray-300">
                  <span className="font-semibold">Cycle Time:</span> {avgCycleTime.toFixed(1)} days average
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  Time from start to completion per item
                </p>
              </div>
            </div>
            
            <div className="flex items-start gap-3">
              <div className="w-2 h-2 rounded-full bg-green-500 mt-2"></div>
              <div>
                <p className="text-sm text-gray-700 dark:text-gray-300">
                  <span className="font-semibold">Flow Efficiency:</span> {flowEfficiency.toFixed(0)}%
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  {flowEfficiency >= 70 ? "Excellent flow!" : flowEfficiency >= 50 ? "Good flow" : "Room for improvement"}
                </p>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Explanation */}
      <CFDDescription />
    </div>
  );
}

