"use client";

// @ts-expect-error - Direct import
import Loader2 from "lucide-react/dist/esm/icons/loader-2";
// @ts-expect-error - Direct import
import CheckCircle from "lucide-react/dist/esm/icons/check-circle";
// @ts-expect-error - Direct import
import AlertCircle from "lucide-react/dist/esm/icons/alert-circle";

interface LoadingItemStatus {
    label: string;
    isLoading: boolean;
    count?: number;
    error?: boolean;
}

interface ViewLoadingDialogProps {
    title: string;
    icon: React.ReactNode;
    items: LoadingItemStatus[];
    isLoading: boolean;
    error?: Error | null;
    children: React.ReactNode;
}

/**
 * A loading dialog that shows while a view's data is loading.
 * Displays loading status for each data type with counts.
 * Shows child content only after all loading is complete.
 */
export function ViewLoadingDialog({
    title,
    icon,
    items,
    isLoading,
    error,
    children,
}: ViewLoadingDialogProps) {
    // Calculate progress
    const completedCount = items.filter(item => !item.isLoading && !item.error).length;
    const totalCount = items.length;
    const progressPercent = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

    // If not loading and no error, show children
    if (!isLoading && !error) {
        return <>{children}</>;
    }

    // Show error state
    if (error) {
        return (
            <div className="h-full w-full flex items-center justify-center bg-muted/20 p-4">
                <div className="bg-card border border-destructive/20 rounded-xl shadow-lg p-6 w-full max-w-sm text-center">
                    <AlertCircle className="w-10 h-10 text-destructive mx-auto mb-3" />
                    <h3 className="text-sm font-semibold text-destructive mb-2">Failed to Load {title}</h3>
                    <p className="text-xs text-muted-foreground">{error.message}</p>
                </div>
            </div>
        );
    }

    // Show loading state
    return (
        <div className="h-full w-full flex items-center justify-center bg-muted/20 p-4">
            <div className="bg-card border rounded-xl shadow-lg p-5 w-full max-w-sm">
                <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold flex items-center gap-2">
                        <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                            {icon}
                        </div>
                        Loading {title}
                    </h3>
                    <span className="text-xs font-mono text-muted-foreground">
                        {progressPercent}%
                    </span>
                </div>

                {/* Progress bar */}
                <div className="w-full h-1.5 bg-muted rounded-full mb-4 overflow-hidden">
                    <div
                        className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full transition-all duration-500 ease-out"
                        style={{ width: `${progressPercent}%` }}
                    />
                </div>

                <div className="space-y-2">
                    {items.map((item, index) => (
                        <LoadingItem key={index} {...item} />
                    ))}
                </div>

                <p className="text-[10px] text-muted-foreground mt-3 text-center">
                    Please wait while data is being fetched...
                </p>
            </div>
        </div>
    );
}

function LoadingItem({ label, isLoading, count, error }: LoadingItemStatus) {
    return (
        <div className="flex items-center justify-between py-1.5 px-2 bg-muted/30 rounded-md">
            <span className="text-xs font-medium">{label}</span>
            <div className="flex items-center gap-1.5">
                {count !== undefined && (
                    <span className={`text-xs font-mono tabular-nums ${error ? 'text-destructive' :
                            isLoading ? 'text-blue-600 dark:text-blue-400' :
                                'text-green-600 dark:text-green-400'
                        }`}>
                        {isLoading ? (count > 0 ? count : "...") : count}
                    </span>
                )}
                {error ? (
                    <AlertCircle className="w-3.5 h-3.5 text-destructive" />
                ) : isLoading ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-500" />
                ) : (
                    <CheckCircle className="w-3.5 h-3.5 text-green-500" />
                )}
            </div>
        </div>
    );
}
