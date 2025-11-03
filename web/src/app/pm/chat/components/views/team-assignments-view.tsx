// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { Card } from "~/components/ui/card";

export function TeamAssignmentsView() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Team Assignments</h2>
      </div>

      <div className="space-y-4">
        <Card className="p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="font-semibold text-gray-900 dark:text-white">👤 John Doe</div>
            <div className="text-sm text-gray-500 dark:text-gray-400">Total: 45h | 75%</div>
          </div>
          <div className="flex gap-2 mb-2">
            <span className="px-2 py-1 bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 rounded text-xs">
              🔴 8h
            </span>
            <span className="px-2 py-1 bg-orange-100 dark:bg-orange-900 text-orange-800 dark:text-orange-200 rounded text-xs">
              🟡 24h
            </span>
            <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded text-xs">
              🔵 13h
            </span>
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Tasks: 12 | Completed: 2
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="font-semibold text-gray-900 dark:text-white">👤 Sarah Smith</div>
            <div className="text-sm text-gray-500 dark:text-gray-400">Total: 38h | 63%</div>
          </div>
          <div className="flex gap-2 mb-2">
            <span className="px-2 py-1 bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 rounded text-xs">
              🔴 12h
            </span>
            <span className="px-2 py-1 bg-orange-100 dark:bg-orange-900 text-orange-800 dark:text-orange-200 rounded text-xs">
              🟡 20h
            </span>
            <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded text-xs">
              🔵 6h
            </span>
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Tasks: 10 | Completed: 2
          </div>
        </Card>
      </div>
    </div>
  );
}

