// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

export function SprintBoardView() {
  const columns = [
    { id: "todo", title: "To Do", count: 8 },
    { id: "in-progress", title: "In Progress", count: 3 },
    { id: "review", title: "Review", count: 2 },
    { id: "done", title: "Done", count: 5 },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Sprint Board</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Sprint 1 - Sep 1 to Sep 15
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
                {column.count}
              </span>
            </div>
            <div className="flex-1 bg-gray-50 dark:bg-gray-900 rounded-b-lg p-3 min-h-[400px] border-2 border-dashed border-gray-300 dark:border-gray-700">
              <div className="text-sm text-gray-500 dark:text-gray-400 text-center">
                Drag tasks here
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

