// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { Card } from "~/components/ui/card";

export function TimelineView() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Timeline</h2>
      </div>

      <Card className="p-6">
        <div className="text-center py-20">
          <div className="text-6xl mb-4">📅</div>
          <div className="text-gray-500 dark:text-gray-400">
            Gantt-style timeline coming soon...
          </div>
        </div>
      </Card>
    </div>
  );
}

