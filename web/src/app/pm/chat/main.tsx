// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { MessagesBlock } from "./components/messages-block";
import { PMViewsPanel } from "./components/pm-views-panel";

export default function Main() {
  return (
    <div className="flex h-full w-full pt-12">
      {/* Chat Panel - Left Side (40%) */}
      <div className="w-[40%] border-r border-gray-200 dark:border-gray-700">
        <MessagesBlock className="h-full" />
      </div>
      
      {/* PM Views Panel - Right Side (60%) */}
      <div className="w-[60%]">
        <PMViewsPanel className="h-full" />
      </div>
    </div>
  );
}
