// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { useMemo } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from "recharts";

import { Card } from "~/components/ui/card";
import { useAllTasks } from "~/core/api/hooks/pm/use-tasks";

export function TimelineView() {
  const { tasks, loading, error } = useAllTasks();

  // Process tasks for Gantt chart
  const ganttData = useMemo(() => {
    const tasksWithDates = tasks.filter(t => t.start_date && t.due_date);
    
    if (tasksWithDates.length === 0) {
      return [];
    }

    // Find min and max dates
    const dates = tasksWithDates.flatMap(t => [
      new Date(t.start_date!),
      new Date(t.due_date!)
    ]);
    const minDate = new Date(Math.min(...dates.map(d => d.getTime())));
    const maxDate = new Date(Math.max(...dates.map(d => d.getTime())));
    
    // Calculate days from start
    const daysFromStart = (date: Date) => {
      return Math.floor((date.getTime() - minDate.getTime()) / (1000 * 60 * 60 * 24));
    };

    return tasksWithDates
      .map(task => {
        const start = new Date(task.start_date!);
        const end = new Date(task.due_date!);
        const startDay = daysFromStart(start);
        const duration = daysFromStart(end) - startDay;
        
        return {
          name: task.title.length > 30 ? task.title.substring(0, 30) + "..." : task.title,
          fullName: task.title,
          start: startDay,
          duration: Math.max(1, duration),
          end: startDay + duration,
          status: task.status,
          priority: task.priority,
          project: task.project_name,
        };
      })
      .sort((a, b) => a.start - b.start)
      .slice(0, 20); // Limit to 20 tasks for readability
  }, [tasks]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-gray-500 dark:text-gray-400">Loading timeline...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-red-500">Error loading timeline: {error.message}</div>
      </div>
    );
  }

  if (ganttData.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Timeline</h2>
        </div>
        <Card className="p-6">
          <div className="text-center py-20">
            <div className="text-6xl mb-4">📅</div>
            <div className="text-gray-500 dark:text-gray-400">
              No tasks with dates available. Tasks need start and due dates to appear on the timeline.
            </div>
          </div>
        </Card>
      </div>
    );
  }

  // Get color based on status/priority
  const getBarColor = (task: typeof ganttData[0]) => {
    if (task.status?.toLowerCase().includes("completed") || task.status?.toLowerCase().includes("done")) {
      return "#10b981"; // green
    }
    if (task.priority === "high" || task.priority === "critical") {
      return "#ef4444"; // red
    }
    if (task.priority === "medium") {
      return "#f59e0b"; // orange
    }
    return "#3b82f6"; // blue
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Timeline</h2>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          Showing {ganttData.length} tasks with dates
        </div>
      </div>

      <Card className="p-6">
        <ResponsiveContainer width="100%" height={Math.max(400, ganttData.length * 40)}>
          <BarChart
            data={ganttData}
            layout="vertical"
            margin={{ top: 20, right: 30, left: 150, bottom: 20 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
            <XAxis 
              type="number"
              domain={[0, 'dataMax']}
              label={{ value: 'Days', position: 'insideBottom', offset: -5 }}
              stroke="#666"
            />
            <YAxis 
              type="category"
              dataKey="name"
              width={140}
              stroke="#666"
            />
            <Tooltip
              contentStyle={{ backgroundColor: 'rgba(255, 255, 255, 0.95)', border: '1px solid #ccc' }}
              formatter={(value: number, name: string) => {
                if (name === 'duration') {
                  return [`${value} days`, 'Duration'];
                }
                return [value, name];
              }}
              labelFormatter={(label, payload) => {
                if (payload?.[0]) {
                  return payload[0].payload.fullName;
                }
                return label;
              }}
            />
            <Bar dataKey="duration" fill="#8884d8" radius={[0, 4, 4, 0]}>
              {ganttData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={getBarColor(entry)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>

        {/* Legend */}
        <div className="mt-6 flex flex-wrap gap-4 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-green-500"></div>
            <span className="text-gray-700 dark:text-gray-300">Completed</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-red-500"></div>
            <span className="text-gray-700 dark:text-gray-300">High Priority</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-orange-500"></div>
            <span className="text-gray-700 dark:text-gray-300">Medium Priority</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-blue-500"></div>
            <span className="text-gray-700 dark:text-gray-300">Normal</span>
          </div>
        </div>
      </Card>
    </div>
  );
}
