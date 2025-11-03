// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState, useEffect } from "react";

import { Button } from "~/components/ui/button";

import { ThemeToggle } from "../../../components/deer-flow/theme-toggle";
import { Tooltip } from "../../../components/deer-flow/tooltip";
import { SettingsDialog } from "../../settings/dialogs/settings-dialog";

const Main = dynamic(() => import("./main"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center">
      Loading Project Management...
    </div>
  ),
});

function ChatPageContent() {
  const searchParams = useSearchParams();
  const projectId = searchParams.get('project');
  const [projectName, setProjectName] = useState<string | null>(null);

  useEffect(() => {
    if (projectId) {
      fetch(`http://localhost:8000/api/projects/${projectId}`, {
        headers: { 'Authorization': 'Bearer mock_token' },
      })
        .then(res => res.json())
        .then(data => setProjectName(data.name))
        .catch(() => setProjectName(null));
    }
  }, [projectId]);

  return (
    <>
      <div className="flex h-screen w-screen justify-center overscroll-none bg-gray-50 dark:bg-gray-900">
        <header className="fixed top-0 left-0 flex h-16 w-full items-center justify-between px-6 bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700 z-50">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-2xl">📊</span>
              <div>
                <h1 className="text-lg font-bold text-gray-900 dark:text-white">
                  {projectName ? `${projectName}` : 'Project Management Agent'}
                </h1>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {projectName ? 'Project-specific chat' : 'AI-Powered Project Planning & Research'}
                </p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Tooltip title="View Projects">
              <Button variant="ghost" size="sm" asChild>
                <Link href="/projects">
                  <span className="mr-2">📁</span>
                  Projects
                </Link>
              </Button>
            </Tooltip>
            <Tooltip title="Return to Research">
              <Button variant="ghost" size="sm" asChild>
                <Link href="/chat">
                  🦌 DeerFlow
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
    </>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={
      <div className="flex h-screen w-screen items-center justify-center">
        Loading Project Management...
      </div>
    }>
      <ChatPageContent />
    </Suspense>
  );
}
