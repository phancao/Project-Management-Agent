// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { Card } from "~/components/ui/card";

export function BacklogView() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Backlog</h2>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          + Add Task
        </button>
      </div>

      <Card className="p-6">
        <div className="space-y-4">
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            Priority Legend: 🔴 High | 🟡 Medium | 🔵 Low
          </div>
          
          <div className="space-y-2">
            <div className="font-semibold text-gray-900 dark:text-white">🔴 HIGH PRIORITY (12 tasks)</div>
            <div className="flex items-center gap-3 p-3 bg-red-50 dark:bg-red-950 rounded-lg border border-red-200 dark:border-red-800">
              <input type="checkbox" className="w-4 h-4" />
              <div className="flex-1">
                <div className="font-medium text-gray-900 dark:text-white">Setup CI/CD Pipeline</div>
                <div className="text-sm text-gray-500 dark:text-gray-400">👤 John Doe | ⏱️ 8h</div>
              </div>
              <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded text-xs">
                High
              </span>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}

