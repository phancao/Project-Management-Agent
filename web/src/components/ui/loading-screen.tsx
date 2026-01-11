"use client";

import React from 'react';
import { FolderKanban } from 'lucide-react';
import { useLoading } from '~/core/contexts/loading-context';
import { usePathname } from 'next/navigation';
import { WorkspaceLoading } from './workspace-loading';

export function LoadingScreen() {
    const { isLoading, message } = useLoading();
    const pathname = usePathname();

    // Don't show loading screen on auth pages
    const isAuthPage = pathname?.startsWith('/login') || pathname?.startsWith('/register');
    if (isAuthPage || !isLoading) return null;

    // Determine which step we're on based on the message
    const isLoadingProviders = message?.toLowerCase().includes('provider');
    const isLoadingProjects = message?.toLowerCase().includes('project');

    const loadingItems = [
        {
            label: "Providers",
            isLoading: isLoadingProviders && !isLoadingProjects,
            isDone: isLoadingProjects,
        },
        {
            label: "Projects",
            isLoading: isLoadingProjects,
            isDone: false,
        },
    ];

    return (
        <WorkspaceLoading
            title="Project Manager"
            subtitle={message || "Initializing workspace..."}
            items={loadingItems}
            icon={<FolderKanban className="w-6 h-6 text-white" />}
            overlay={true}
        />
    );
}
