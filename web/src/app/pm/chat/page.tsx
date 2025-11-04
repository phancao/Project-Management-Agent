// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import dynamic from "next/dynamic";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { PMHeader } from "../components/pm-header";

const Main = dynamic(() => import("./main"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center">
      Loading Project Management...
    </div>
  ),
});

function ChatPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const selectedProjectId = searchParams.get('project');

  const handleProjectChange = (projectId: string) => {
    router.push(`/pm/chat?project=${projectId}`);
  };

  return (
    <>
      <PMHeader selectedProjectId={selectedProjectId} onProjectChange={handleProjectChange} />
      <div className="flex h-screen w-screen justify-center overscroll-none bg-gray-50 dark:bg-gray-900 pt-16">
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
