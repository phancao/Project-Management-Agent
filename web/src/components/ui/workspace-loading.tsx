"use client";

import { cn } from "~/lib/utils";
import { Badge } from "~/components/ui/badge";
import { useSettingsStore, type LoadingTheme } from "~/core/store";
// @ts-expect-error - Direct import
import Loader2 from "lucide-react/dist/esm/icons/loader-2";
// @ts-expect-error - Direct import
import Users from "lucide-react/dist/esm/icons/users";

// Theme color mappings
const THEME_COLORS: Record<LoadingTheme, {
    gradient: string;
    shadow: string;
    spinner: string;
    darkShadow: string;
}> = {
    indigo: {
        gradient: 'from-indigo-500 to-violet-600',
        shadow: 'shadow-indigo-500/30',
        spinner: 'text-indigo-500 dark:text-indigo-400',
        darkShadow: 'dark:shadow-indigo-500/10',
    },
    blue: {
        gradient: 'from-blue-500 to-cyan-600',
        shadow: 'shadow-blue-500/30',
        spinner: 'text-blue-500 dark:text-blue-400',
        darkShadow: 'dark:shadow-blue-500/10',
    },
    purple: {
        gradient: 'from-purple-500 to-pink-600',
        shadow: 'shadow-purple-500/30',
        spinner: 'text-purple-500 dark:text-purple-400',
        darkShadow: 'dark:shadow-purple-500/10',
    },
    emerald: {
        gradient: 'from-emerald-500 to-teal-600',
        shadow: 'shadow-emerald-500/30',
        spinner: 'text-emerald-500 dark:text-emerald-400',
        darkShadow: 'dark:shadow-emerald-500/10',
    },
    amber: {
        gradient: 'from-amber-500 to-orange-600',
        shadow: 'shadow-amber-500/30',
        spinner: 'text-amber-500 dark:text-amber-400',
        darkShadow: 'dark:shadow-amber-500/10',
    },
    rose: {
        gradient: 'from-rose-500 to-pink-600',
        shadow: 'shadow-rose-500/30',
        spinner: 'text-rose-500 dark:text-rose-400',
        darkShadow: 'dark:shadow-rose-500/10',
    },
};

export interface LoadingItem {
    label: string;
    isLoading: boolean;
    count?: number;
    /** Optional: if true, this item is done loading. If false, it's waiting to start. If not provided, derives from isLoading. */
    isDone?: boolean;
}

export interface WorkspaceLoadingProps {
    title?: string;
    subtitle?: string;
    items: LoadingItem[];
    /** Custom icon component to display in the header */
    icon?: React.ReactNode;
    /** Whether to show as a fixed overlay or inline */
    overlay?: boolean;
    /** Height for inline mode */
    height?: string;
    /** Override theme color (if not provided, uses settings) */
    colorTheme?: LoadingTheme;
}

/**
 * Premium Workspace Loading Component
 * 
 * A consistent, theme-aware loading UI that shows progress of multiple data sources.
 * Supports both light and dark themes with configurable accent colors.
 */
export function WorkspaceLoading({
    title = "Initializing Workspace",
    subtitle = "Gathering team data...",
    items,
    icon,
    overlay = false,
    height = "h-[600px]",
    colorTheme,
}: WorkspaceLoadingProps) {
    // Get theme from settings if not provided
    const settingsTheme = useSettingsStore((state) => state.appearance?.loadingTheme || 'indigo');
    const theme = colorTheme || settingsTheme;
    const colors = THEME_COLORS[theme];

    const content = (
        <div className={cn(
            "bg-white dark:bg-gradient-to-br dark:from-slate-900 dark:to-slate-800 border border-gray-200 dark:border-slate-700/50 rounded-2xl shadow-xl dark:shadow-2xl p-8 w-full max-w-sm backdrop-blur-sm",
            colors.darkShadow
        )}>
            {/* Header */}
            <div className="flex items-center gap-4 mb-6">
                <div className={cn(
                    "w-12 h-12 bg-gradient-to-br rounded-xl flex items-center justify-center shadow-lg",
                    colors.gradient,
                    colors.shadow
                )}>
                    {icon || <Users className="w-6 h-6 text-white" />}
                </div>
                <div>
                    <h3 className="text-base font-bold text-gray-900 dark:text-white">{title}</h3>
                    <p className="text-sm text-gray-500 dark:text-slate-400">{subtitle}</p>
                </div>
            </div>

            {/* Loading Items */}
            <div className="space-y-3">
                {items.map((item) => {
                    // Determine if item is done: either explicit isDone, or !isLoading with a count
                    const isDone = item.isDone !== undefined ? item.isDone : (!item.isLoading && (item.count !== undefined && item.count > 0));

                    return (
                        <div key={item.label} className="flex items-center gap-3">
                            {item.isLoading ? (
                                <Loader2 className={cn("w-4 h-4 animate-spin", colors.spinner)} />
                            ) : isDone ? (
                                <div className="w-4 h-4 rounded-full bg-emerald-500 flex items-center justify-center">
                                    <span className="text-[8px] text-white">✓</span>
                                </div>
                            ) : (
                                // Pending state - empty circle
                                <div className="w-4 h-4 rounded-full border-2 border-gray-300 dark:border-slate-600" />
                            )}
                            <span className={cn(
                                "text-sm",
                                item.isLoading ? "text-gray-500 dark:text-slate-400" :
                                    isDone ? "text-gray-700 dark:text-slate-200" :
                                        "text-gray-400 dark:text-slate-500"
                            )}>
                                {item.label}
                            </span>
                            {isDone && item.count !== undefined && item.count > 0 && (
                                <Badge className="ml-auto bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-slate-300 text-[10px] hover:bg-gray-100 dark:hover:bg-slate-700">
                                    {item.count}
                                </Badge>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );

    if (overlay) {
        return (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm transition-opacity duration-300">
                {content}
            </div>
        );
    }

    return (
        <div className={cn(height, "w-full flex items-center justify-center p-4")}>
            {content}
        </div>
    );
}

/**
 * Simple inline loading spinner with optional message.
 * For use within components that need a lightweight loading state.
 */
export function InlineLoading({ message = "Loading..." }: { message?: string }) {
    const theme = useSettingsStore((state) => state.appearance?.loadingTheme || 'indigo');
    const colors = THEME_COLORS[theme];

    return (
        <div className="flex items-center justify-center py-12">
            <div className="flex flex-col items-center gap-3">
                <Loader2 className={cn("h-8 w-8 animate-spin", colors.spinner)} />
                <p className="text-sm text-gray-500 dark:text-slate-400">{message}</p>
            </div>
        </div>
    );
}
