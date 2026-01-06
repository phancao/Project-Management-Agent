"use client";

import React from 'react';
import { Loader2, FolderKanban, Server, Briefcase, Zap } from 'lucide-react';
import { useLoading } from '~/core/contexts/loading-context';

export function LoadingScreen() {
    const { isLoading, message } = useLoading();

    if (!isLoading) return null;

    // Determine which step we're on based on the message
    const isLoadingProviders = message?.toLowerCase().includes('provider');
    const isLoadingProjects = message?.toLowerCase().includes('project');

    // Calculate progress (providers = 50%, projects = 100%)
    const progressPercent = isLoadingProviders ? 25 : isLoadingProjects ? 75 : 50;

    const loadingItems = [
        {
            label: "Providers",
            icon: Server,
            isLoading: isLoadingProviders,
            isDone: isLoadingProjects,
            description: "Connecting to PM backends"
        },
        {
            label: "Projects",
            icon: Briefcase,
            isLoading: isLoadingProjects,
            isDone: false,
            description: "Loading project data"
        },
    ];

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm transition-opacity duration-300">
            <div className="bg-card border rounded-2xl shadow-2xl p-8 w-full max-w-md mx-4">
                {/* Header */}
                <div className="flex items-center gap-4 mb-6">
                    <div className="w-14 h-14 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg">
                        <FolderKanban className="w-7 h-7 text-white" />
                    </div>
                    <div>
                        <h2 className="text-xl font-bold text-foreground">Project Manager</h2>
                        <p className="text-sm text-muted-foreground">Initializing workspace...</p>
                    </div>
                </div>

                {/* Progress bar */}
                <div className="w-full h-2 bg-muted rounded-full mb-6 overflow-hidden">
                    <div
                        className="h-full bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500 rounded-full transition-all duration-700 ease-out"
                        style={{ width: `${progressPercent}%` }}
                    />
                </div>

                {/* Loading items */}
                <div className="space-y-3 mb-6">
                    {loadingItems.map((item, index) => {
                        const Icon = item.icon;
                        const isActive = item.isLoading;
                        const isDone = item.isDone;

                        return (
                            <div
                                key={index}
                                className={`flex items-center justify-between py-3 px-4 rounded-lg transition-all duration-300 ${isActive
                                        ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800'
                                        : isDone
                                            ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
                                            : 'bg-muted/30 border border-transparent'
                                    }`}
                            >
                                <div className="flex items-center gap-3">
                                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${isActive
                                            ? 'bg-blue-100 dark:bg-blue-900/50'
                                            : isDone
                                                ? 'bg-green-100 dark:bg-green-900/50'
                                                : 'bg-muted'
                                        }`}>
                                        <Icon className={`w-4 h-4 ${isActive
                                                ? 'text-blue-600 dark:text-blue-400'
                                                : isDone
                                                    ? 'text-green-600 dark:text-green-400'
                                                    : 'text-muted-foreground'
                                            }`} />
                                    </div>
                                    <div>
                                        <span className={`text-sm font-medium ${isActive || isDone ? 'text-foreground' : 'text-muted-foreground'
                                            }`}>
                                            {item.label}
                                        </span>
                                        <p className="text-xs text-muted-foreground">{item.description}</p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    {isActive ? (
                                        <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
                                    ) : isDone ? (
                                        <div className="w-5 h-5 rounded-full bg-green-500 flex items-center justify-center">
                                            <span className="text-white text-xs">✓</span>
                                        </div>
                                    ) : (
                                        <div className="w-5 h-5 rounded-full border-2 border-muted-foreground/30" />
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
                    <Zap className="w-3 h-3" />
                    <span>{message || "Loading..."}</span>
                </div>
            </div>
        </div>
    );
}
