// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useContextTokens } from "~/hooks/use-context-tokens";
import { cn } from "~/lib/utils";

/**
 * Context token indicator component.
 * Displays current token usage vs limit with progress bar, similar to Cursor's indicator.
 */
export function ContextTokenIndicator({ className }: { className?: string }) {
  const { tokenCount, tokenLimit, percentage, modelName } = useContextTokens();

  // Color coding based on usage percentage
  const getColorClass = () => {
    if (percentage >= 90) return "text-red-500 dark:text-red-400";
    if (percentage >= 75) return "text-orange-500 dark:text-orange-400";
    if (percentage >= 50) return "text-yellow-500 dark:text-yellow-400";
    return "text-muted-foreground";
  };

  // Progress bar color based on usage
  const getProgressColor = () => {
    if (percentage >= 90) return "bg-red-500 dark:bg-red-400";
    if (percentage >= 75) return "bg-orange-500 dark:bg-orange-400";
    if (percentage >= 50) return "bg-yellow-500 dark:bg-yellow-400";
    return "bg-blue-500 dark:bg-blue-400";
  };

  // Format numbers with K/M suffixes for large values
  const formatNumber = (num: number) => {
    if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
    if (num >= 10_000) return `${(num / 1_000).toFixed(0)}K`;
    if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
    return num.toLocaleString();
  };

  // Status text based on usage
  const getStatusText = () => {
    if (percentage >= 90) return "⚠️ Near limit";
    if (percentage >= 75) return "Context filling up";
    return "";
  };

  return (
    <div
      className={cn(
        "flex flex-col gap-1",
        className
      )}
      title={`Context: ${tokenCount.toLocaleString()} / ${tokenLimit.toLocaleString()} tokens (${percentage.toFixed(1)}%)\nModel: ${modelName}\n\nContext optimization runs automatically when limit is exceeded.`}
    >
      {/* Token count display */}
      <div className={cn("flex items-center gap-1.5 text-xs font-mono", getColorClass())}>
        <span className="tabular-nums">
          {formatNumber(tokenCount)}
        </span>
        <span className="text-muted-foreground/60">/</span>
        <span className="tabular-nums text-muted-foreground/80">
          {formatNumber(tokenLimit)}
        </span>
        {percentage >= 50 && (
          <span className="ml-1 text-[10px] opacity-70">
            ({percentage.toFixed(0)}%)
          </span>
        )}
      </div>

      {/* Progress bar (only show when usage is notable) */}
      {percentage >= 25 && (
        <div className="h-1 w-full rounded-full bg-muted/50 overflow-hidden">
          <div
            className={cn("h-full rounded-full transition-all duration-300", getProgressColor())}
            style={{ width: `${Math.min(100, percentage)}%` }}
          />
        </div>
      )}

      {/* Status text for high usage */}
      {getStatusText() && (
        <span className={cn("text-[10px]", getColorClass())}>
          {getStatusText()}
        </span>
      )}
    </div>
  );
}

