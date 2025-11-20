// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import dynamic from "next/dynamic";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { PMHeader } from "../components/pm-header";
import { PMLoadingProvider } from "../context/pm-loading-context";
import { PMLoadingManager } from "../components/pm-loading-manager";

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

const Main = dynamic(() => import("./main"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center">
      Loading Project Management...
    </div>
  ),
  onError: (error) => {
    console.error("Failed to load Main component:", error);
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
