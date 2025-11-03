// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { Card } from "~/components/ui/card";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area } from "recharts";
import { useMyTasks } from "~/core/api/hooks/pm/use-tasks";

export function BurndownView() {
  const { tasks, loading, error } = useMyTasks();

  // Calculate burndown data from tasks
  const totalHours = tasks.reduce((sum, t) => sum + (t.estimated_hours || 0), 0);
  const completedHours = tasks
    .filter(t => t.status && (t.status.toLowerCase().includes("done") || t.status.toLowerCase().includes("completed")))
    .reduce((sum, t) => sum + (t.estimated_hours || 0), 0);
  const remainingHours = totalHours - completedHours;

  // Generate dummy burndown data for visualization
  const days = ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6", "Day 7", "Day 8", "Day 9", "Day 10"];
  const idealBurndown = days.map((_, i) => totalHours * (1 - i / days.length));
  const actualBurndown = days.map((_, i) => {
    if (i < 2) return totalHours * 0.95;
    if (i < 4) return totalHours * 0.85;
    if (i < 6) return totalHours * 0.70;
    if (i < 8) return totalHours * 0.45;
    return totalHours * 0.20;
  });
  
  const burndownData = days.map((day, i) => ({
    day,
    ideal: idealBurndown[i],
    actual: actualBurndown[i],
  }));

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
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Burndown Chart</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Sprint Overview - {tasks.length} tasks
          </p>
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Total Estimated</div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">{totalHours.toFixed(1)}h</div>
        </Card>
        <Card className="p-4">
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Completed</div>
          <div className="text-2xl font-bold text-green-600">{completedHours.toFixed(1)}h</div>
        </Card>
        <Card className="p-4">
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Remaining</div>
          <div className="text-2xl font-bold text-orange-600">{remainingHours.toFixed(1)}h</div>
        </Card>
        <Card className="p-4">
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Progress</div>
          <div className="text-2xl font-bold text-blue-600">
            {totalHours > 0 ? ((completedHours / totalHours) * 100).toFixed(0) : 0}%
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

      {/* Task Breakdown */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Task Breakdown</h3>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <div className="text-sm text-gray-500 dark:text-gray-400 mb-2">To Do</div>
            <div className="text-3xl font-bold text-gray-700 dark:text-gray-300">
              {tasks.filter(t => !t.status || t.status === "None" || t.status.toLowerCase().includes("todo")).length}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-500 dark:text-gray-400 mb-2">In Progress</div>
            <div className="text-3xl font-bold text-orange-600">
              {tasks.filter(t => t.status && t.status.toLowerCase().includes("progress")).length}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-500 dark:text-gray-400 mb-2">Done</div>
            <div className="text-3xl font-bold text-green-600">
              {tasks.filter(t => t.status && (t.status.toLowerCase().includes("done") || t.status.toLowerCase().includes("completed"))).length}
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}

