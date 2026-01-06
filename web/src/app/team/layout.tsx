'use client';

import { Suspense } from 'react';
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PMLoadingProvider } from "../pm/context/pm-loading-context";
import { PMLoadingManager } from "../pm/components/pm-loading-manager";
import { TeamDataProvider } from "./context/team-data-context";

// Create a client - persistent across navigations in this layout
const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            refetchOnWindowFocus: false,
            retry: 1,
        },
    },
});

export default function TeamLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <Suspense fallback={<div className="flex h-screen w-screen items-center justify-center">Loading Team Workspace...</div>}>
            <QueryClientProvider client={queryClient}>
                <PMLoadingProvider>
                    <PMLoadingManager />
                    <TeamDataProvider>
                        {children}
                    </TeamDataProvider>
                </PMLoadingProvider>
            </QueryClientProvider>
        </Suspense>
    );
}
