// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { useMyTasks } from "~/core/api/hooks/pm/use-tasks";

export function SprintBoardView() {
  const { tasks, loading, error } = useMyTasks();

  // Group tasks by status
  const todoTasks = tasks.filter(t => 
    !t.status || t.status === "None" || t.status.toLowerCase().includes("todo") || t.status.toLowerCase().includes("new")
  );
  const inProgressTasks = tasks.filter(t => 
    t.status && (t.status.toLowerCase().includes("progress") || t.status.toLowerCase().includes("in_progress"))
  );
  const reviewTasks = tasks.filter(t => 
    t.status && (t.status.toLowerCase().includes("review") || t.status.toLowerCase().includes("pending"))
  );
  const doneTasks = tasks.filter(t => 
    t.status && (t.status.toLowerCase().includes("done") || t.status.toLowerCase().includes("completed") || t.status.toLowerCase().includes("closed"))
  );

  const columns = [
    { id: "todo", title: "To Do", tasks: todoTasks },
    { id: "in-progress", title: "In Progress", tasks: inProgressTasks },
    { id: "review", title: "Review", tasks: reviewTasks },
    { id: "done", title: "Done", tasks: doneTasks },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-gray-500 dark:text-gray-400">Loading board...</div>
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
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Sprint Board</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            My Tasks - {tasks.length} total
          </p>
        </div>
      </div>

      {/* Kanban Board */}
      <div className="grid grid-cols-4 gap-4">
        {columns.map((column) => (
          <div key={column.id} className="flex flex-col">
            <div className="flex items-center justify-between p-3 bg-gray-100 dark:bg-gray-800 rounded-t-lg">
              <h3 className="font-semibold text-gray-900 dark:text-white">{column.title}</h3>
              <span className="px-2 py-1 bg-white dark:bg-gray-700 rounded text-sm font-medium text-gray-700 dark:text-gray-300">
                {column.tasks.length}
              </span>
            </div>
            <div className="flex-1 bg-gray-50 dark:bg-gray-900 rounded-b-lg p-3 min-h-[400px] border border-gray-200 dark:border-gray-700 overflow-y-auto">
              {column.tasks.length === 0 ? (
                <div className="text-sm text-gray-500 dark:text-gray-400 text-center py-8">
                  No tasks
                </div>
              ) : (
                <div className="space-y-2">
                  {column.tasks.map((task) => (
                    <div
                      key={task.id}
                      className="p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow cursor-move"
                    >
                      <div className="font-medium text-sm text-gray-900 dark:text-white mb-2">
                        {task.title}
                      </div>
                      <div className="flex items-center gap-2 text-xs">
                        {task.priority && (
                          <span className={`px-2 py-0.5 rounded ${
                            task.priority === "high" ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200" :
                            task.priority === "medium" ? "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200" :
                            "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                          }`}>
                            {task.priority}
                          </span>
                        )}
                        {task.estimated_hours && (
                          <span className="text-gray-500 dark:text-gray-400">
                            ⏱️ {task.estimated_hours}h
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

