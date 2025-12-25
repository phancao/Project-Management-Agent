// Copyright (c) 2025
// SPDX-License-Identifier: MIT

/**
 * PlannerAnalysisBlock Component (formerly AnalysisBlock)
 * 
 * Displays Planner agent analysis results with JSON plan parsing:
 * - Waits for complete JSON plan before displaying
 * - Shows structured plan with steps
 * - Green color scheme to differentiate from ReAct
 * - Actions: copy, download, edit
 */

import { motion, AnimatePresence } from "framer-motion";
import {
  Check,
  ChevronDown,
  ChevronUp,
  Copy,
  Download,
  Pencil,
  Undo2,
  Brain,
  Sparkles,
  Loader2
} from "lucide-react";
import { useTranslations } from "next-intl";
import React, { useCallback, useMemo, useState } from "react";

import { LoadingAnimation } from "~/components/deer-flow/loading-animation";
import { Markdown } from "~/components/deer-flow/markdown";
import { RainbowText } from "~/components/deer-flow/rainbow-text";
import { Tooltip } from "~/components/deer-flow/tooltip";
import ReportEditor from "~/components/editor";
import { Button } from "~/components/ui/button";
import { Card, CardContent, CardHeader } from "~/components/ui/card";
import { useReplay } from "~/core/replay";
import { useMessage, useStore } from "~/core/store";
import { parseJSON } from "~/core/utils";
import { cn } from "~/lib/utils";

import { StepBox } from "./step-box";
import { ThoughtBox } from "./thought-box";
import { plannerTheme } from "./analysis-themes";
import { useResearchThoughts } from "../hooks/use-research-thoughts";

interface PlannerAnalysisBlockProps {
  className?: string;
  researchId: string;
}

export function PlannerAnalysisBlock({ className, researchId }: PlannerAnalysisBlockProps) {
  const { isReplay } = useReplay();

  // Get research data from store
  const plannerResearchIds = useStore((state) => state.plannerResearchIds);
  const researchIds = useStore((state) => state.researchIds);
  const reportId = useStore((state) => state.researchReportIds.get(researchId));
  const activityIds = useStore((state) => state.researchActivityIds.get(researchId)) ?? [];
  const planMessageId = useStore((state) => state.researchPlanIds.get(researchId));
  const ongoing = useStore((state) => state.ongoingResearchId === researchId);
  const messages = useStore((state) => state.messages) ?? new Map();

  const reportMessage = useMessage(reportId ?? "");
  const planMessage = useMessage(planMessageId ?? "");

  const hasReport = reportId !== undefined && reportMessage?.content;
  const isGeneratingReport = reportMessage?.isStreaming ?? false;

  // Get title and plan content from plan
  const planData = useMemo(() => {
    if (planMessage?.content) {
      return parseJSON(planMessage.content, { title: "", thought: "", steps: [] });
    }
    if (reportMessage?.content) {
      const firstLine = reportMessage.content.split('\n')[0]?.trim();
      if (firstLine && firstLine.length < 100) {
        return { title: firstLine.replace(/^#+\s*/, ""), thought: "", steps: [] };
      }
    }
    if (reportId || activityIds.length > 0) {
      return { title: "Analysis", thought: "", steps: [] };
    }
    return { title: "", thought: "", steps: [] };
  }, [planMessage?.content, reportMessage?.content, reportId, activityIds.length]);

  const title = planData.title;

  // Determine if block should be shown
  const validResearchIds = researchIds.filter(id => id != null && id !== undefined);
  const hasPlannerResearchId = plannerResearchIds.includes(researchId);
  const hasResearchId = validResearchIds.includes(researchId);
  const hasContent = title || reportId || activityIds.length > 0 || ongoing || planMessageId;
  const shouldShow = hasPlannerResearchId || hasResearchId || hasContent;

  if (!shouldShow) {
    return null;
  }

  const isLoading = hasResearchId && !hasContent;

  // Collect all tool calls from activities - now reactive to messages changes
  // Also track which agent each tool call came from
  const toolCalls = useMemo(() => {
    const calls: Array<{
      id: string;
      name: string;
      args: Record<string, unknown>;
      result?: string;
      agent?: string;
    }> = [];

    if (!messages || !activityIds || activityIds.length === 0) {
      return calls;
    }

    for (const activityId of activityIds) {
      const message = messages.get(activityId);
      if (message?.toolCalls) {
        for (const tc of message.toolCalls) {
          // Skip error results
          if (typeof tc.result === "string" && tc.result.startsWith("Error")) {
            continue;
          }
          calls.push({
            ...tc,
            agent: message.agent, // Include agent info
          });
        }
      }
    }

    return calls;
  }, [activityIds, messages]);

  // Cursor-style: Collect thoughts using the dedicated hook
  // Extracts from plan steps and pm_agent/react_agent reactThoughts
  const thoughts = useResearchThoughts(researchId);

  // DEBUG: Log thoughts and tool calls for debugging
  const renderTimestamp = new Date().toISOString();
  console.log(`[AnalysisBlock] 📋 [${renderTimestamp}] Rendering: researchId=${researchId}`, {
    thoughtsCount: thoughts.length,
    toolCallsCount: toolCalls.length,
    thoughts: thoughts.map(t => ({ step_index: t.step_index, agent: t.agent, thought: t.thought.substring(0, 50) })),
    toolCalls: toolCalls.map(tc => ({ id: tc.id, name: tc.name, hasResult: !!tc.result })),
  });

  // UI state
  const [stepsExpanded, setStepsExpanded] = useState(true);
  const [editing, setEditing] = useState(false);
  const [copied, setCopied] = useState(false);

  // Handlers
  const handleCopy = useCallback(() => {
    if (!reportMessage?.content) return;
    void navigator.clipboard.writeText(reportMessage.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1000);
  }, [reportMessage?.content]);

  const handleDownload = useCallback(() => {
    if (!reportMessage?.content) return;
    const now = new Date();
    const pad = (n: number) => n.toString().padStart(2, '0');
    const timestamp = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}_${pad(now.getHours())}-${pad(now.getMinutes())}`;
    const filename = `analysis-${timestamp}.md`;
    const blob = new Blob([reportMessage.content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, 0);
  }, [reportMessage?.content]);

  const handleEdit = useCallback(() => {
    setEditing((prev) => !prev);
  }, []);

  const handleMarkdownChange = useCallback((markdown: string) => {
    if (reportMessage) {
      reportMessage.content = markdown;
      useStore.setState({
        messages: new Map(useStore.getState().messages).set(reportMessage.id, reportMessage),
      });
    }
  }, [reportMessage]);

  // Status text
  const statusText = useMemo(() => {
    if (hasReport && !isGeneratingReport) return "Analysis complete";
    if (isGeneratingReport) return "Generating insights...";
    if (ongoing) return "Analyzing...";
    return "Processing...";
  }, [hasReport, isGeneratingReport, ongoing]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn("w-full", className)}
      style={{ minWidth: 0, maxWidth: '100%' }}
    >
      <Card className={cn(
        "overflow-hidden overflow-x-hidden w-full border-2",
        plannerTheme.border,
        plannerTheme.background
      )} style={{ minWidth: 0, maxWidth: '100%', overflowX: 'hidden' }}>
        {/* Header */}
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={cn(
                "p-2 rounded-lg bg-gradient-to-br",
                plannerTheme.iconBg
              )}>
                <Brain size={20} className={cn(plannerTheme.text)} />
              </div>
              <div>
                <div className={cn(
                  "text-lg font-semibold",
                  plannerTheme.text
                )}>
                  {title || plannerTheme.name}
                </div>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  {(ongoing || isGeneratingReport) && (
                    <Loader2 size={12} className="animate-spin" />
                  )}
                  {!ongoing && !isGeneratingReport && hasReport && (
                    <Sparkles size={12} className="text-green-500" />
                  )}
                  <span>{statusText}</span>
                </div>
              </div>
            </div>

            {/* Actions */}
            {hasReport && !isGeneratingReport && (
              <div className="flex items-center gap-1">
                <Tooltip title={editing ? "Cancel edit" : "Edit"}>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-8 w-8"
                    disabled={isReplay}
                    onClick={handleEdit}
                  >
                    {editing ? <Undo2 size={16} /> : <Pencil size={16} />}
                  </Button>
                </Tooltip>
                <Tooltip title="Copy">
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-8 w-8"
                    onClick={handleCopy}
                  >
                    {copied ? <Check size={16} /> : <Copy size={16} />}
                  </Button>
                </Tooltip>
                <Tooltip title="Download as markdown">
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-8 w-8"
                    onClick={handleDownload}
                  >
                    <Download size={16} />
                  </Button>
                </Tooltip>
              </div>
            )}
          </div>
        </CardHeader>

        <CardContent className="pt-0 overflow-x-hidden break-words [word-break:break-word] [overflow-wrap:anywhere]" style={{ overflowX: 'hidden', wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
          {/* Loading indicator when no tool calls yet */}
          {toolCalls.length === 0 && thoughts.length === 0 && ongoing && (
            <div className="py-4">
              <LoadingAnimation />
            </div>
          )}

          {/* Plan Content Section - Show planner thought and full plan JSON */}
          {planMessage?.content && (
            <div className="mb-4 pb-4 border-b break-words [word-break:break-word] [overflow-wrap:anywhere]">
              {/* Show planner's thought if available */}
              {planData.thought && (
                <div className="mb-3">
                  <div className="prose prose-sm dark:prose-invert max-w-none break-words [word-break:break-word] [overflow-wrap:anywhere]">
                    <Markdown animated={false}>
                      {planData.thought}
                    </Markdown>
                  </div>
                </div>
              )}

              {/* Show full plan JSON in a collapsible code block */}
              <details className="mt-2">
                <summary className="cursor-pointer text-sm text-muted-foreground hover:text-foreground transition-colors">
                  📋 View Full Plan JSON
                </summary>
                <div className="mt-2 p-3 bg-muted rounded-md overflow-x-auto">
                  <pre className="text-xs font-mono whitespace-pre-wrap break-words">
                    {planMessage.content}
                  </pre>
                </div>
              </details>
              {/* NOTE: Step descriptions are extracted and shown in ThoughtBox in Steps section */}
            </div>
          )}

          {/* Steps Section - Collapsible (FIRST) */}
          {(toolCalls.length > 0 || thoughts.length > 0) && (
            <div className="mb-4">
              <button
                className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors w-full py-2"
                onClick={() => setStepsExpanded(!stepsExpanded)}
              >
                {stepsExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                <span className="font-medium">Steps</span>
                <span className="text-xs bg-accent px-2 py-0.5 rounded-full">
                  {toolCalls.length + thoughts.length}
                </span>
              </button>

              <AnimatePresence>
                {stepsExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden overflow-x-hidden break-words [word-break:break-word] [overflow-wrap:anywhere]"
                    style={{ overflowX: 'hidden', wordBreak: 'break-word', overflowWrap: 'anywhere' }}
                  >
                    <div className="flex flex-col gap-0.5 pt-0.5 overflow-x-hidden break-words [word-break:break-word] [overflow-wrap:anywhere]" style={{ overflowX: 'hidden', wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                      {/* Cursor-style: Interleave thoughts and tool calls - thoughts appear BEFORE their tool call */}
                      {(() => {
                        // Create a combined list of thoughts and tool calls
                        // Thoughts should appear BEFORE the tool call at the same step_index
                        const combinedSteps: Array<{
                          type: 'thought' | 'tool';
                          data: any;
                          sortKey: number; // Used for sorting - lower appears first
                        }> = [];

                        // Add thoughts - use step_index as sort key, but subtract 0.5 so they appear BEFORE tools
                        thoughts.forEach((thought) => {
                          combinedSteps.push({
                            type: 'thought',
                            data: thought,
                            // Thoughts appear BEFORE tools at the same index
                            // Use step_index - 0.5 so thought at index 0 appears before tool at index 0
                            sortKey: thought.step_index - 0.5,
                          });
                        });

                        // Add tool calls - use their index as sort key
                        toolCalls.forEach((toolCall, toolIndex) => {
                          combinedSteps.push({
                            type: 'tool',
                            data: toolCall,
                            sortKey: toolIndex,
                          });
                        });

                        // Sort by sortKey to maintain order (thoughts before tools at same index)
                        combinedSteps.sort((a, b) => a.sortKey - b.sortKey);

                        const totalSteps = combinedSteps.length;

                        return combinedSteps.map((step, displayIndex) => {
                          if (step.type === 'thought') {
                            return (
                              <ThoughtBox
                                key={`thought-${step.data.step_index}-${displayIndex}`}
                                thought={step.data.thought}
                                stepNumber={displayIndex + 1}
                                totalSteps={totalSteps}
                                defaultExpanded={true}  // Always show thoughts expanded so users can see AI thinking
                              />
                            );
                          } else {
                            return (
                              <StepBox
                                key={step.data.id}
                                toolCall={step.data}
                                stepNumber={displayIndex + 1}
                                totalSteps={ongoing ? undefined : totalSteps}
                                agent={step.data.agent}
                              />
                            );
                          }
                        });
                      })()}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}

          {/* Report/Insights Section - Inline (BELOW steps) */}
          {(hasReport || isGeneratingReport) && (
            <div className={cn((toolCalls.length > 0 || thoughts.length > 0) ? "border-t pt-4" : "", "break-words [word-break:break-word] [overflow-wrap:anywhere]")}>
              <div className="flex items-center gap-2 mb-3">
                <Sparkles size={16} className="text-amber-500" />
                <span className="font-medium text-sm">Insights</span>
              </div>

              {!isReplay && hasReport && !isGeneratingReport && editing ? (
                <ReportEditor
                  content={reportMessage?.content}
                  onMarkdownChange={handleMarkdownChange}
                />
              ) : (
                <div className="prose prose-sm dark:prose-invert max-w-none break-words [word-break:break-word] [overflow-wrap:anywhere]">
                  <Markdown animated={isGeneratingReport} checkLinkCredibility>
                    {reportMessage?.content ?? ""}
                  </Markdown>
                  {isGeneratingReport && (
                    <LoadingAnimation className="my-4" />
                  )}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
