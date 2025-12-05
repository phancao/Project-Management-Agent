// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useContextTokens } from "~/hooks/use-context-tokens";
import { cn } from "~/lib/utils";

/**
 * Context token indicator component.
 * Displays current token usage vs limit, similar to Cursor's indicator.
 */
export function ContextTokenIndicator({ className }: { className?: string }) {
  const { tokenCount, tokenLimit, percentage } = useContextTokens();
  
  // Color coding based on usage percentage
  const getColorClass = () => {
    if (percentage >= 90) return "text-red-500 dark:text-red-400";
    if (percentage >= 75) return "text-orange-500 dark:text-orange-400";
    if (percentage >= 50) return "text-yellow-500 dark:text-yellow-400";
    return "text-muted-foreground";
  };
  
  // Format numbers with commas
  const formatNumber = (num: number) => {
    return num.toLocaleString();
  };
  
  return (
    <div
      className={cn(
        "flex items-center gap-1.5 text-xs font-mono",
        getColorClass(),
        className
      )}
      title={`Context tokens: ${formatNumber(tokenCount)} / ${formatNumber(tokenLimit)} (${percentage.toFixed(1)}%)`}
    >
      <span className="tabular-nums">
        {formatNumber(tokenCount)}
      </span>
      <span className="text-muted-foreground/60">/</span>
      <span className="tabular-nums text-muted-foreground/80">
        {formatNumber(tokenLimit)}
      </span>
      {percentage >= 75 && (
        <span className="ml-1 text-[10px] opacity-70">
          ({percentage.toFixed(0)}%)
        </span>
      )}
    </div>
  );
}

