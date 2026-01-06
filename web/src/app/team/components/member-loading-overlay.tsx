"use client";

import { Loader2, User, CheckSquare, Building2, Zap } from "lucide-react";

interface MemberLoadingOverlayProps {
    isContextLoading: boolean;
    isLoadingUsers: boolean;
    isLoadingTasks: boolean;
}

/**
 * Branded loading overlay for Member Profile page.
 * Tracks initialization of Workspace, User Roster, and Task History.
 */
export function MemberLoadingOverlay({
    isContextLoading,
    isLoadingUsers,
    isLoadingTasks
}: MemberLoadingOverlayProps) {
    const isAnyLoading = isContextLoading || isLoadingUsers || isLoadingTasks;

    if (!isAnyLoading) {
        return null;
    }

    // Calculate progress
    const loadingItems = [
        {
            label: "Workspace Context",
            icon: Building2,
            isLoading: isContextLoading,
            isDone: !isContextLoading,
            description: "Syncing teams & projects"
        },
        {
            label: "Member Profile",
            icon: User,
            isLoading: isLoadingUsers,
            isDone: !isLoadingUsers,
            description: "Fetching user details"
        },
        {
            label: "Work History",
            icon: CheckSquare,
            isLoading: isLoadingTasks,
            isDone: !isLoadingTasks,
            description: "Retrieving assignments & worklogs"
        }
    ];

    const completedCount = loadingItems.filter(item => item.isDone).length;
    const progressPercent = Math.round((completedCount / loadingItems.length) * 100);

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm transition-opacity duration-300">
            <div className="bg-card border rounded-2xl shadow-2xl p-8 w-full max-w-md mx-4">
                {/* Header */}
                <div className="flex items-center gap-4 mb-6">
                    <div className="w-14 h-14 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg">
                        <User className="w-7 h-7 text-white" />
                    </div>
                    <div>
                        <h2 className="text-xl font-bold text-foreground">Member Profile</h2>
                        <p className="text-sm text-muted-foreground">Gathering workload metrics...</p>
                    </div>
                </div>

                {/* Progress bar */}
                <div className="w-full h-2 bg-muted rounded-full mb-6 overflow-hidden">
                    <div
                        className="h-full bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 rounded-full transition-all duration-500 ease-out"
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
                                    ? 'bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800'
                                    : isDone
                                        ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
                                        : 'bg-muted/30 border border-transparent'
                                    }`}
                            >
                                <div className="flex items-center gap-3">
                                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${isActive
                                        ? 'bg-indigo-100 dark:bg-indigo-900/50'
                                        : isDone
                                            ? 'bg-green-100 dark:bg-green-900/50'
                                            : 'bg-muted'
                                        }`}>
                                        <Icon className={`w-4 h-4 ${isActive
                                            ? 'text-indigo-600 dark:text-indigo-400'
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
                                        <Loader2 className="w-5 h-5 animate-spin text-indigo-500" />
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
                    <span>Analyzing performance data...</span>
                </div>
            </div>
        </div>
    );
}
