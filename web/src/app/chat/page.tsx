// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { Suspense } from "react";

import { Button } from "~/components/ui/button";

import { ThemeToggle } from "../../components/deer-flow/theme-toggle";
import { Tooltip } from "../../components/deer-flow/tooltip";
import { SettingsDialog } from "../settings/dialogs/settings-dialog";

const Main = dynamic(() => import("./main"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center">
      Loading DeerFlow...
    </div>
  ),
});

function ChatPageContent() {
  return (
    <div className="flex h-screen w-screen justify-center overscroll-none bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-gray-900 dark:to-gray-800">
      <header className="fixed top-0 left-0 flex h-16 w-full items-center justify-between px-6 bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700 z-50">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-2xl">🦌</span>
            <div>
              <h1 className="text-lg font-bold text-gray-900 dark:text-white">
                DeerFlow
              </h1>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Deep Research Assistant
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Tooltip title="View Projects">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/pm/chat">
                <span className="mr-2">📊</span>
                Project Management
              </Link>
            </Button>
          </Tooltip>
          <ThemeToggle />
          <Suspense>
            <SettingsDialog />
          </Suspense>
        </div>
      </header>
      <Main />
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={
      <div className="flex h-screen w-screen items-center justify-center">
        Loading DeerFlow...
      </div>
    }>
      <ChatPageContent />
    </Suspense>
  );
}
