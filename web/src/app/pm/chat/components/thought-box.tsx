// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

/**
 * ThoughtBox Component
 * 
 * Displays "Thought" steps (reasoning) like Cursor does.
 * Shows the agent's reasoning before taking an action.
 */

import { motion } from "framer-motion";
import { Brain } from "lucide-react";
import React from "react";

import { Card } from "~/components/ui/card";
import { cn } from "~/lib/utils";
import { Markdown } from "~/components/deer-flow/markdown";

interface ThoughtBoxProps {
  thought: string;
  stepNumber?: number;
  totalSteps?: number;
  className?: string;
  defaultExpanded?: boolean;
}

export function ThoughtBox({ 
  thought, 
  stepNumber,
  totalSteps,
  className,
  defaultExpanded = true  // Default to expanded so users can see AI thinking
}: ThoughtBoxProps) {
  const [isExpanded, setIsExpanded] = React.useState(defaultExpanded);
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={cn("w-full", className)}
    >
      <Card 
        className={cn(
          "overflow-hidden transition-all duration-200 py-0 gap-0",
          "border-purple-200/50 bg-purple-50/30 dark:bg-purple-950/10 dark:border-purple-800/30"
        )}
      >
        {/* Header - always visible */}
        <button
          className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-purple-100/50 dark:hover:bg-purple-900/20 transition-colors"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          {/* Thought icon */}
          <div className="shrink-0">
            <Brain size={14} className="text-purple-600 dark:text-purple-400" />
          </div>
          
          {/* Thought label */}
          <div className="flex items-center gap-1 shrink-0">
            <span className="font-medium text-xs text-purple-900 dark:text-purple-100">Thought</span>
          </div>
          
          {/* Step number */}
          {stepNumber !== undefined && (
            <span className="text-[10px] text-purple-700 dark:text-purple-300 bg-purple-100 dark:bg-purple-900/30 px-1.5 py-px rounded-full">
              {totalSteps !== undefined ? `${stepNumber}/${totalSteps}` : `#${stepNumber}`}
            </span>
          )}
          
          {/* Expand icon */}
          <div className="shrink-0 text-purple-600 dark:text-purple-400 ml-auto">
            {isExpanded ? (
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M3.5 8.75L7 5.25L10.5 8.75" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            ) : (
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M5.25 3.5L8.75 7L5.25 10.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            )}
          </div>
        </button>
        
        {/* Expanded content */}
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="border-t border-purple-200/50 dark:border-purple-800/30"
          >
            <div className="p-3 max-h-[400px] overflow-y-auto">
              <div className="prose prose-sm dark:prose-invert max-w-none text-purple-900 dark:text-purple-100 break-words [word-break:break-word] [overflow-wrap:anywhere]">
                <Markdown animated={false}>
                  {thought}
                </Markdown>
              </div>
            </div>
          </motion.div>
        )}
      </Card>
    </motion.div>
  );
}

