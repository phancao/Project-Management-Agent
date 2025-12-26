// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

/**
 * ThoughtBox Component
 * 
 * Displays "Thought" steps (reasoning) like Cursor does.
 * Shows the agent's reasoning before taking an action.
 * 
 * Styled consistently with StepBox - same size, padding, text.
 * Uses Brand Color: Pantone 233 CP (Magenta) #CE007C
 */

import { motion } from "framer-motion";
import { Brain, ChevronRight, ChevronDown } from "lucide-react";
import React, { useMemo } from "react";

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

// Helper to get a clean preview of the thought content
function getThoughtPreview(thought: string, maxLength: number = 120): string {
  let preview = thought.trim();

  // Remove markdown formatting for preview
  preview = preview
    .replace(/```[\s\S]*?```/g, '[code]')
    .replace(/`[^`]+`/g, '[code]')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/#{1,6}\s+/g, '')
    .replace(/\n+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  if (preview.length > maxLength) {
    return preview.substring(0, maxLength).trim() + '...';
  }
  return preview;
}

export function ThoughtBox({
  thought,
  stepNumber,
  totalSteps,
  className,
  defaultExpanded = false
}: ThoughtBoxProps) {
  const [isExpanded, setIsExpanded] = React.useState(defaultExpanded);

  const preview = useMemo(() => getThoughtPreview(thought), [thought]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={cn("w-full", className)}
      style={{ minWidth: 0, maxWidth: '100%' }}
    >
      <Card
        className={cn(
          "overflow-hidden transition-all duration-200 py-0 gap-0 w-full",
          // Brand: Magenta #CE007C
          "border-[#CE007C]/30 bg-white dark:bg-[#CE007C]/10"
        )}
        style={{ minWidth: 0, maxWidth: '100%' }}
      >
        {/* Header - matches StepBox layout exactly */}
        <button
          className="grid w-full grid-cols-[auto_auto_auto_1fr_auto] items-center gap-1 px-2 py-0.5 text-left hover:bg-[#CE007C]/10 transition-colors"
          style={{ minWidth: 0 }}
          onClick={() => setIsExpanded(!isExpanded)}
        >
          {/* Icon - matches StepBox status icon size */}
          <div className="shrink-0 text-[#CE007C]">
            <Brain size={12} />
          </div>

          {/* Label - matches StepBox tool name style */}
          <span className="font-medium text-xs text-[#CE007C] shrink-0">Thought</span>

          {/* Step number - matches StepBox badge style */}
          {stepNumber !== undefined && (
            <span className="text-[10px] text-[#CE007C] bg-[#CE007C]/10 px-1.5 py-px rounded-full shrink-0">
              {totalSteps !== undefined ? `${stepNumber}/${totalSteps}` : `#${stepNumber}`}
            </span>
          )}

          {/* Preview text - matches StepBox summary style */}
          <span
            className="text-xs text-[#CE007C]/70 truncate min-w-0"
            style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
          >
            {preview}
          </span>

          {/* Expand icon - matches StepBox */}
          <div className="shrink-0 text-[#CE007C]">
            {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </div>
        </button>

        {/* Expanded content */}
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="border-t border-[#CE007C]/20"
          >
            <div className="px-2.5 py-2">
              {/* Force text size to 11px, relaxed leading, standard font for clean look */}
              <div className="prose prose-sm dark:prose-invert max-w-none text-foreground dark:text-[#CE007C]/90 break-words [word-break:break-word] [overflow-wrap:anywhere] font-sans marker:font-sans prose-headings:font-sans prose-p:font-sans prose-li:font-sans prose-ol:list-decimal prose-ul:list-disc [&>*:first-child]:mt-0 [&>*:last-child]:mb-0 [&_p]:my-0.5 [&_p]:!text-[11px] [&_li]:!text-[11px] [&_span]:!text-[11px] !text-[11px] leading-relaxed">
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
