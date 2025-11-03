// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { Card } from "~/components/ui/card";

export function DashboardView() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h2>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4 bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
          <div className="text-sm text-blue-600 dark:text-blue-400 font-medium">Total Projects</div>
          <div className="text-3xl font-bold text-blue-900 dark:text-blue-100 mt-2">3</div>
        </Card>
        <Card className="p-4 bg-purple-50 dark:bg-purple-950 border-purple-200 dark:border-purple-800">
          <div className="text-sm text-purple-600 dark:text-purple-400 font-medium">Active Sprints</div>
          <div className="text-3xl font-bold text-purple-900 dark:text-purple-100 mt-2">5</div>
        </Card>
        <Card className="p-4 bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800">
          <div className="text-sm text-green-600 dark:text-green-400 font-medium">Open Tasks</div>
          <div className="text-3xl font-bold text-green-900 dark:text-green-100 mt-2">42</div>
        </Card>
        <Card className="p-4 bg-orange-50 dark:bg-orange-950 border-orange-200 dark:border-orange-800">
          <div className="text-sm text-orange-600 dark:text-orange-400 font-medium">My Tasks</div>
          <div className="text-3xl font-bold text-orange-900 dark:text-orange-100 mt-2">12</div>
        </Card>
      </div>

      {/* My Work Section */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">My Work</h3>
        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <div>
              <div className="font-medium text-gray-900 dark:text-white">Setup Database Schema</div>
              <div className="text-sm text-gray-500 dark:text-gray-400">E-commerce Platform</div>
            </div>
            <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded text-xs font-medium">
              In Progress
            </span>
          </div>
        </div>
      </Card>

      {/* Project Summary */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Project Summary</h3>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          Dashboard coming soon...
        </div>
      </Card>
    </div>
  );
}

