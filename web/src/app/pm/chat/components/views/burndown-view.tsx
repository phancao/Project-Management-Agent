// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { Card } from "~/components/ui/card";

export function BurndownView() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Burndown Chart</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Sprint 1 - Sep 1 to Sep 15
          </p>
        </div>
      </div>

      <Card className="p-6">
        <div className="text-center py-20">
          <div className="text-6xl mb-4">📉</div>
          <div className="text-gray-500 dark:text-gray-400">
            Burndown chart visualization coming soon...
          </div>
        </div>
      </Card>
    </div>
  );
}

