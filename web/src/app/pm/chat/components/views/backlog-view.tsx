// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { Card } from "~/components/ui/card";
import { useMyTasks } from "~/core/api/hooks/pm/use-tasks";

export function BacklogView() {
  const { tasks, loading, error } = useMyTasks();

  const highPriority = tasks.filter(t => t.priority === "high" || t.priority === "highest" || t.priority === "critical");
  const mediumPriority = tasks.filter(t => t.priority === "medium");
  const lowPriority = tasks.filter(t => t.priority === "low" || t.priority === "lowest");
  const noPriority = tasks.filter(t => !t.priority || t.priority === "None");

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-gray-500 dark:text-gray-400">Loading backlog...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-red-500">Error loading tasks: {error.message}</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Backlog</h2>
      </div>

      <Card className="p-6">
        <div className="space-y-4">
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            Priority Legend: 🔴 High | 🟡 Medium | 🔵 Low
          </div>
          
          {highPriority.length > 0 && (
            <div className="space-y-2">
              <div className="font-semibold text-gray-900 dark:text-white">
                🔴 HIGH PRIORITY ({highPriority.length} tasks)
              </div>
              {highPriority.map((task) => (
                <div key={task.id} className="flex items-center gap-3 p-3 bg-red-50 dark:bg-red-950 rounded-lg border border-red-200 dark:border-red-800">
                  <input type="checkbox" className="w-4 h-4" />
                  <div className="flex-1">
                    <div className="font-medium text-gray-900 dark:text-white">{task.title}</div>
                    {task.assigned_to && (
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        👤 {task.assigned_to} {task.estimated_hours && `| ⏱️ ${task.estimated_hours}h`}
                      </div>
                    )}
                  </div>
                  <span className="px-2 py-1 bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 rounded text-xs">
                    High
                  </span>
                </div>
              ))}
            </div>
          )}

          {mediumPriority.length > 0 && (
            <div className="space-y-2 pt-4">
              <div className="font-semibold text-gray-900 dark:text-white">
                🟡 MEDIUM PRIORITY ({mediumPriority.length} tasks)
              </div>
              {mediumPriority.map((task) => (
                <div key={task.id} className="flex items-center gap-3 p-3 bg-orange-50 dark:bg-orange-950 rounded-lg border border-orange-200 dark:border-orange-800">
                  <input type="checkbox" className="w-4 h-4" />
                  <div className="flex-1">
                    <div className="font-medium text-gray-900 dark:text-white">{task.title}</div>
                    {task.assigned_to && (
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        👤 {task.assigned_to} {task.estimated_hours && `| ⏱️ ${task.estimated_hours}h`}
                      </div>
                    )}
                  </div>
                  <span className="px-2 py-1 bg-orange-100 dark:bg-orange-900 text-orange-800 dark:text-orange-200 rounded text-xs">
                    Medium
                  </span>
                </div>
              ))}
            </div>
          )}

          {lowPriority.length > 0 && (
            <div className="space-y-2 pt-4">
              <div className="font-semibold text-gray-900 dark:text-white">
                🔵 LOW PRIORITY ({lowPriority.length} tasks)
              </div>
              {lowPriority.map((task) => (
                <div key={task.id} className="flex items-center gap-3 p-3 bg-blue-50 dark:bg-blue-950 rounded-lg border border-blue-200 dark:border-blue-800">
                  <input type="checkbox" className="w-4 h-4" />
                  <div className="flex-1">
                    <div className="font-medium text-gray-900 dark:text-white">{task.title}</div>
                    {task.assigned_to && (
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        👤 {task.assigned_to} {task.estimated_hours && `| ⏱️ ${task.estimated_hours}h`}
                      </div>
                    )}
                  </div>
                  <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded text-xs">
                    Low
                  </span>
                </div>
              ))}
            </div>
          )}

          {noPriority.length > 0 && (
            <div className="space-y-2 pt-4">
              <div className="font-semibold text-gray-900 dark:text-white">
                📋 NO PRIORITY ({noPriority.length} tasks)
              </div>
              {noPriority.map((task) => (
                <div key={task.id} className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-950 rounded-lg border border-gray-200 dark:border-gray-800">
                  <input type="checkbox" className="w-4 h-4" />
                  <div className="flex-1">
                    <div className="font-medium text-gray-900 dark:text-white">{task.title}</div>
                    {task.estimated_hours && (
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        ⏱️ {task.estimated_hours}h
                      </div>
                    )}
                  </div>
                  <span className="px-2 py-1 bg-gray-100 dark:bg-gray-900 text-gray-800 dark:text-gray-200 rounded text-xs">
                    {task.status}
                  </span>
                </div>
              ))}
            </div>
          )}

          {tasks.length === 0 && (
            <div className="text-center py-12 text-gray-500 dark:text-gray-400">
              No tasks in backlog
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}

