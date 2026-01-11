"use client";

import { cn } from "~/lib/utils";
import { Badge } from "~/components/ui/badge";
import { useThemeColors, THEME_COLORS } from "~/core/hooks/use-theme-colors";
import type { AccentColor } from "~/core/store";
// @ts-expect-error - Direct import
import Loader2 from "lucide-react/dist/esm/icons/loader-2";
// @ts-expect-error - Direct import
import Users from "lucide-react/dist/esm/icons/users";

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
    colorTheme?: AccentColor;
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
    const { accent, accentColorName } = useThemeColors();
    const colors = colorTheme ? THEME_COLORS[colorTheme] : accent;

    const content = (
        <div className={cn(
            "bg-card rounded-2xl border border-gray-200 dark:border-0 shadow-xl dark:shadow-2xl dark:shadow-indigo-500/5 p-8 w-full max-w-sm backdrop-blur-sm",
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
                    <h3 className="text-base font-bold text-foreground">{title}</h3>
                    <p className="text-sm text-muted-foreground">{subtitle}</p>
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
                                <div className="w-4 h-4 rounded-full border-2 border-muted-foreground/30" />
                            )}
                            <span className={cn(
                                "text-sm",
                                item.isLoading ? "text-muted-foreground" :
                                    isDone ? "text-foreground" :
                                        "text-muted-foreground/60"
                            )}>
                                {item.label}
                            </span>
                            {isDone && item.count !== undefined && item.count > 0 && (
                                <Badge className="ml-auto bg-muted text-muted-foreground text-[10px] hover:bg-muted">
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
    const { accent } = useThemeColors();

    return (
        <div className="flex items-center justify-center py-12">
            <div className="flex flex-col items-center gap-3">
                <Loader2 className={cn("h-8 w-8 animate-spin", accent.spinner)} />
                <p className="text-sm text-muted-foreground">{message}</p>
            </div>
        </div>
    );
}
