// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

/**
 * HandoverIndicator Component
 * 
 * Visual indicator showing ReAct → Planner escalation
 * Displays between ReAct and Planner analysis blocks
 */

import { ArrowRight } from "lucide-react";
import React from "react";
import { cn } from "~/lib/utils";

interface HandoverIndicatorProps {
  className?: string;
}

export function HandoverIndicator({ className }: HandoverIndicatorProps) {
  return (
    <div className={cn(
      "flex items-center justify-center gap-2 py-2 px-4",
      "bg-gradient-to-r from-blue-100 to-green-100",
      "dark:from-blue-900/30 dark:to-green-900/30",
      "border-y border-blue-300 dark:border-blue-700",
      className
    )}>
      <div className="flex items-center gap-2 text-sm">
        <span className="text-blue-600 dark:text-blue-400 font-medium">ReAct</span>
        <ArrowRight size={16} className="text-muted-foreground" />
        <span className="text-green-600 dark:text-green-400 font-medium">Planner</span>
      </div>
      <span className="text-xs text-muted-foreground">Escalated</span>
    </div>
  );
}




