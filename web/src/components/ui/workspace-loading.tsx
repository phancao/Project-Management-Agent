"use client";

import { cn } from "~/lib/utils";
import { Badge } from "~/components/ui/badge";
// @ts-expect-error - Direct import
import Loader2 from "lucide-react/dist/esm/icons/loader-2";
// @ts-expect-error - Direct import
import Users from "lucide-react/dist/esm/icons/users";

export interface LoadingItem {
    label: string;
    isLoading: boolean;
    count?: number;
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
}

/**
 * Premium Workspace Loading Component
 * 
 * A consistent, theme-aware loading UI that shows progress of multiple data sources.
 * Supports both light and dark themes with the "Initializing Workspace" design pattern.
 * 
 * @example
 * ```tsx
 * <WorkspaceLoading
 *   title="Initializing Workspace"
 *   subtitle="Gathering team data..."
 *   items={[
 *     { label: "Users", isLoading: false, count: 8 },
 *     { label: "Tasks", isLoading: true, count: 1862 },
 *     { label: "Projects", isLoading: true },
 *   ]}
 * />
 * ```
 */
export function WorkspaceLoading({
    title = "Initializing Workspace",
    subtitle = "Gathering team data...",
    items,
    icon,
    overlay = false,
    height = "h-[600px]",
}: WorkspaceLoadingProps) {
    const content = (
        <div className="bg-white dark:bg-gradient-to-br dark:from-slate-900 dark:to-slate-800 border border-gray-200 dark:border-slate-700/50 rounded-2xl shadow-xl dark:shadow-2xl dark:shadow-indigo-500/10 p-8 w-full max-w-sm backdrop-blur-sm">
            {/* Header */}
            <div className="flex items-center gap-4 mb-6">
                <div className="w-12 h-12 bg-gradient-to-br from-indigo-500 to-violet-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/30">
                    {icon || <Users className="w-6 h-6 text-white" />}
                </div>
                <div>
                    <h3 className="text-base font-bold text-gray-900 dark:text-white">{title}</h3>
                    <p className="text-sm text-gray-500 dark:text-slate-400">{subtitle}</p>
                </div>
            </div>

            {/* Loading Items */}
            <div className="space-y-3">
                {items.map((item) => (
                    <div key={item.label} className="flex items-center gap-3">
                        {item.isLoading ? (
                            <Loader2 className="w-4 h-4 animate-spin text-indigo-500 dark:text-indigo-400" />
                        ) : (
                            <div className="w-4 h-4 rounded-full bg-emerald-500 flex items-center justify-center">
                                <span className="text-[8px] text-white">✓</span>
                            </div>
                        )}
                        <span className={cn(
                            "text-sm",
                            item.isLoading ? "text-gray-500 dark:text-slate-400" : "text-gray-700 dark:text-slate-200"
                        )}>
                            {item.label}
                        </span>
                        {!item.isLoading && item.count !== undefined && item.count > 0 && (
                            <Badge className="ml-auto bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-slate-300 text-[10px] hover:bg-gray-100 dark:hover:bg-slate-700">
                                {item.count}
                            </Badge>
                        )}
                    </div>
                ))}
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
    return (
        <div className="flex items-center justify-center py-12">
            <div className="flex flex-col items-center gap-3">
                <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
                <p className="text-sm text-gray-500 dark:text-slate-400">{message}</p>
            </div>
        </div>
    );
}
