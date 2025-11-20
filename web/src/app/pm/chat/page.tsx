// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { PMHeader } from "../components/pm-header";
import { PMLoadingProvider } from "../context/pm-loading-context";
import { PMLoadingManager } from "../components/pm-loading-manager";
import Main from "./main";

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

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
        <PMLoadingManager />
        {/* Section 1: Floating Header */}
        <PMHeader selectedProjectId={selectedProjectId} onProjectChange={handleProjectChange} />
        
        {/* Section 2: Left Pane + Section 3: Upper Body + Content Area */}
        <div className="flex h-screen w-screen justify-center overscroll-none bg-gray-50 dark:bg-gray-900 pt-16">
          <Main />
        </div>
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
