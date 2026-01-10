// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { PMHeader } from "../components/pm-header";
import { PMLoadingProvider } from "../context/pm-loading-context";
import { PMDataProvider, usePMDataContext } from "../context/pm-data-context";
import { PMLoadingManager } from "../components/pm-loading-manager";
import Main from "./main";
import { useLoading } from "~/core/contexts/loading-context";

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

/**
 * PMContent renders Main only after the initial blocking load completes.
 * This prevents views from fetching heavy data (tasks, users) during the blocking overlay.
 */
function PMContent() {
  const { isLoading: isLoadingContext } = usePMDataContext();
  const { isLoading: isLoadingGlobal } = useLoading();

  // Don't render Main until initial load is complete
  if (isLoadingContext || isLoadingGlobal) {
    return null;
  }

  return <Main />;
}

function ChatPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedProjectId = searchParams.get('project');

  const handleProjectChange = (projectId: string) => {
    router.push(`/pm/chat?project=${projectId}`);
  };

  return (
    <QueryClientProvider client={queryClient}>
      <PMLoadingProvider>
        <PMDataProvider>
          <PMLoadingManager />
          {/* Section 1: Floating Header */}
          <PMHeader selectedProjectId={selectedProjectId} onProjectChange={handleProjectChange} />

          {/* Section 2: Left Pane + Section 3: Upper Body + Content Area */}
          <div className="flex h-screen w-screen justify-center overscroll-none bg-transparent pt-16">
            <PMContent />
          </div>
        </PMDataProvider>
      </PMLoadingProvider>
    </QueryClientProvider>
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
