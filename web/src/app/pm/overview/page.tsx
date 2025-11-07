// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { Suspense } from "react";

import { DashboardView } from "../chat/components/views/dashboard-view";
import { PMHeader } from "../components/pm-header";
import { PMLoadingProvider } from "../context/pm-loading-context";
import { PMLoadingManager } from "../components/pm-loading-manager";

function OverviewPageContent() {
  return (
    <PMLoadingProvider>
      <PMLoadingManager />
      <PMHeader />
      <div className="flex h-screen w-screen flex-col bg-gray-50 dark:bg-gray-900 pt-16">
        <div className="flex-1 overflow-auto p-6">
          <DashboardView />
        </div>
      </div>
    </PMLoadingProvider>
  );
}

export default function OverviewPage() {
  return (
    <Suspense fallback={
      <div className="flex h-screen w-screen items-center justify-center">
        Loading...
      </div>
    }>
      <OverviewPageContent />
    </Suspense>
  );
}
