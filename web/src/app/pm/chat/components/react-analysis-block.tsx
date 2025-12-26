// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

/**
 * ReActAnalysisBlock Component
 * 
 * Displays ReAct agent analysis results with token-by-token streaming:
 * - No JSON parsing wait - content streams immediately
 * - Real-time thoughts and tool calls display
 * - Blue/cyan color scheme to differentiate from Planner
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
  Zap,
  Sparkles,
  Loader2
} from "lucide-react";
import React, { useCallback, useMemo, useState } from "react";

import { LoadingAnimation } from "~/components/deer-flow/loading-animation";
import { Markdown } from "~/components/deer-flow/markdown";
import { Tooltip } from "~/components/deer-flow/tooltip";
import ReportEditor from "~/components/editor";
import { Button } from "~/components/ui/button";
import { Card, CardContent, CardHeader } from "~/components/ui/card";
import { useReplay } from "~/core/replay";
import { useMessage, useStore } from "~/core/store";
import { cn } from "~/lib/utils";

import { StepBox } from "./step-box";
import { ThoughtBox } from "./thought-box";
import { reactTheme } from "./analysis-themes";
import { useResearchThoughts } from "../hooks/use-research-thoughts";

interface ReActAnalysisBlockProps {
  className?: string;
  researchId: string;
}

export function ReActAnalysisBlockV2({ className, researchId }: ReActAnalysisBlockProps) {
  const { isReplay } = useReplay();

  // Get research data from store
  const reactResearchIds = useStore((state) => state.reactResearchIds);
  const reportId = useStore((state) => state.researchReportIds.get(researchId));
  const activityIds = useStore((state) => state.researchActivityIds.get(researchId)) ?? [];
  const ongoing = useStore((state) => state.ongoingResearchId === researchId);
  const messages = useStore((state) => state.messages) ?? new Map();

  // Check if ReAct escalated to Planner
  const escalationLink = useStore((state) => state.reactToPlannerEscalation.get(researchId));
  const hasEscalated = !!escalationLink;

  // For ReAct: Get the main message (not plan message - ReAct doesn't use JSON plans)
  const reactMessage = useMessage(researchId);
  const reportMessage = useMessage(reportId ?? "");

  const hasReport = reportId !== undefined && reportMessage?.content;
  const isGeneratingReport = reportMessage?.isStreaming ?? false;

  // Get title from ReAct message content or default
  const title = useMemo(() => {
    // ReAct doesn't have a plan, so get title from message content or default
    if (reactMessage?.content) {
      // Try to extract title from first line of content
      const firstLine = reactMessage.content.split('\n')[0]?.trim();
      if (firstLine && firstLine.length < 100 && !firstLine.startsWith('Thought:')) {
        return firstLine.replace(/^#+\s*/, "");
      }
    }
    if (reportMessage?.content) {
      const firstLine = reportMessage.content.split('\n')[0]?.trim();
      if (firstLine && firstLine.length < 100) {
        return firstLine.replace(/^#+\s*/, "");
      }
    }
    if (reportId || activityIds.length > 0) {
      return reactTheme.name;
    }
    return reactTheme.name;
  }, [reactMessage?.content, reportMessage?.content, reportId, activityIds.length]);

  // Determine if block should be shown
  const hasResearchId = reactResearchIds.includes(researchId);
  const hasContent = title || reportId || activityIds.length > 0 || ongoing || reactMessage;
  const shouldShow = hasResearchId || hasContent;

  if (!shouldShow) {
    return null;
  }

  const isLoading = hasResearchId && !hasContent;

  // Collect all tool calls from activities
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
            agent: message.agent,
          });
        }
      }
    }

    return calls;
  }, [activityIds, messages]);

  // Collect thoughts using the dedicated hook
  const thoughts = useResearchThoughts(researchId);

  // UI state
  const [stepsExpanded, setStepsExpanded] = useState(true);
  const [editing, setEditing] = useState(false);
  const [copied, setCopied] = useState(false);

  // Handlers
  const handleCopy = useCallback(() => {
    const contentToCopy = reportMessage?.content || reactMessage?.content || "";
    if (!contentToCopy) return;
    void navigator.clipboard.writeText(contentToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 1000);
  }, [reportMessage?.content, reactMessage?.content]);

  const handleDownload = useCallback(() => {
    const contentToDownload = reportMessage?.content || reactMessage?.content || "";
    if (!contentToDownload) return;
    const now = new Date();
    const pad = (n: number) => n.toString().padStart(2, '0');
    const timestamp = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}_${pad(now.getHours())}-${pad(now.getMinutes())}`;
    const filename = `react-analysis-${timestamp}.md`;
    const blob = new Blob([contentToDownload], { type: 'text/markdown' });
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
  }, [reportMessage?.content, reactMessage?.content]);

  const handleEdit = useCallback(() => {
    setEditing((prev) => !prev);
  }, []);

  const handleMarkdownChange = useCallback((markdown: string) => {
    if (reportMessage) {
      reportMessage.content = markdown;
      useStore.setState({
        messages: new Map(useStore.getState().messages).set(reportMessage.id, reportMessage),
      });
    } else if (reactMessage) {
      reactMessage.content = markdown;
      useStore.setState({
        messages: new Map(useStore.getState().messages).set(reactMessage.id, reactMessage),
      });
    }
  }, [reportMessage, reactMessage]);

  // Status text
  const statusText = useMemo(() => {
    if (hasEscalated) return "Escalated to Planner";
    if (hasReport && !isGeneratingReport) return "Analysis complete";
    if (isGeneratingReport) return "Generating insights...";
    if (ongoing && !hasEscalated) return "Analyzing...";
    return "Processing...";
  }, [hasReport, isGeneratingReport, ongoing, hasEscalated]);

  // Get streaming content from ReAct message (token-by-token)
  const reactContent = reactMessage?.content || "";
  const isStreamingContent = reactMessage?.isStreaming ?? false;

  // Loading Logic: Stop spinning if report exists and not regenerating
  const showSpinner = (ongoing || isGeneratingReport || isStreamingContent) && (!hasReport || isGeneratingReport);
  // Show sparkles if complete
  const showSparkles = !showSpinner && hasReport;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn("w-full max-w-full overflow-hidden", className)}
      style={{ minWidth: 0, maxWidth: '100%' }}
    >
      <Card className={cn(
        "overflow-hidden overflow-x-hidden w-full border-2 max-w-full",
        reactTheme.border,
        reactTheme.background
      )} style={{ minWidth: 0, maxWidth: '100%', overflowX: 'hidden' }}>
        {/* Header */}
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={cn(
                "p-2 rounded-lg bg-gradient-to-br",
                reactTheme.iconBg
              )}>
                <Zap size={20} className={cn(reactTheme.text)} />
              </div>
              <div>
                <div className={cn(
                  "text-lg font-semibold",
                  reactTheme.text
                )}>
                  {title}
                </div>
                <div className="flex items-center gap-2 text-sm text-foreground/80 dark:text-muted-foreground">
                  {showSpinner && (
                    <Loader2 size={12} className="animate-spin" />
                  )}
                  {showSparkles && (
                    <Sparkles size={12} className="text-[#162B75]" />
                  )}
                  <span>{statusText}</span>
                </div>
              </div>
            </div>

            {/* Actions */}
            {(hasReport || reactContent) && !isGeneratingReport && !isStreamingContent && (
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
          {toolCalls.length === 0 && thoughts.length === 0 && ongoing && !reactContent && (
            <div className="py-4">
              <LoadingAnimation />
            </div>
          )}

          {/* ReAct Content Section - Stream token-by-token (no JSON parsing) */}
          {reactContent && (
            <div className="mb-4 pb-4 border-b break-words [word-break:break-word] [overflow-wrap:anywhere]">
              <div className="prose prose-sm dark:prose-invert max-w-none break-words [word-break:break-word] [overflow-wrap:anywhere] overflow-x-auto w-full">
                <Markdown animated={isStreamingContent} checkLinkCredibility>
                  {reactContent}
                </Markdown>
                {isStreamingContent && (
                  <LoadingAnimation className="my-4" />
                )}
              </div>
            </div>
          )}

          {/* Steps Section - Collapsible */}
          {(toolCalls.length > 0 || thoughts.length > 0) && (
            <div className="mb-4">
              <button
                className="flex items-center gap-2 text-sm text-foreground/80 dark:text-muted-foreground hover:text-foreground transition-colors w-full py-2"
                onClick={() => setStepsExpanded(!stepsExpanded)}
              >
                {stepsExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                <span className="font-medium">Steps</span>
                <span className="text-xs bg-accent px-2 py-0.5 rounded-full">
                  {toolCalls.length + thoughts.length}
                </span>
                {/* DEBUG MARKER */}
                <span className="text-[10px] bg-red-500 text-white px-1 rounded">v2</span>
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
                    <div className="flex flex-col gap-0.5 pt-0.5 overflow-x-hidden break-words [word-break:break-word] [overflow-wrap:anywhere] min-w-0" style={{ overflowX: 'hidden', wordBreak: 'break-word', overflowWrap: 'anywhere' }}>
                      {/* Interleave thoughts and tool calls */}
                      {(() => {
                        const combinedSteps: Array<{
                          type: 'thought' | 'tool';
                          data: any;
                          sortKey: number;
                        }> = [];

                        // Add thoughts
                        thoughts.forEach((thought) => {
                          combinedSteps.push({
                            type: 'thought',
                            data: thought,
                            sortKey: thought.step_index - 0.5,
                          });
                        });

                        // Add tool calls
                        toolCalls.forEach((toolCall, toolIndex) => {
                          combinedSteps.push({
                            type: 'tool',
                            data: toolCall,
                            sortKey: toolIndex,
                          });
                        });

                        // Sort by sortKey
                        combinedSteps.sort((a, b) => a.sortKey - b.sortKey);

                        const totalSteps = combinedSteps.length;

                        // DEBUG: Log combined steps
                        console.log(`[ReActAnalysisBlock] 🕒 [${new Date().toISOString()}] Steps Analysis (v2):`, {
                          total: combinedSteps.length,
                          rawSteps: combinedSteps.map(s => ({
                            type: s.type,
                            index: s.data.step_index,
                            content_preview: s.type === 'thought' ? s.data.thought.substring(0, 50) : s.data.name,
                            has_tool_call: s.type === 'thought' ? s.data.thought.includes('TOOL_CALL:') : false,
                            has_tool_result: s.type === 'thought' ? s.data.thought.includes('TOOL_RESULT:') : false
                          }))
                        });

                        const finalSteps: Array<any> = [];
                        const consumedIndices = new Set<number>();

                        for (let i = 0; i < combinedSteps.length; i++) {
                          if (consumedIndices.has(i)) continue;

                          const step = combinedSteps[i];
                          if (!step) continue;

                          if (step.type === 'thought') {
                            const content = step.data.thought;
                            // Check for TOOL_CALL
                            if (content.includes('TOOL_CALL:')) {
                              // Parse name and args
                              // Allow empty name: TOOL_CALL: ({}) -> name=""
                              const match = content.match(/TOOL_CALL:\s*([^(]*)\(([\s\S]*)\)/);
                              const name = match && match[1].trim() ? match[1].trim() : "tool";
                              const args = match ? match[2].trim() : "{}";

                              // Look ahead for TOOL_RESULT
                              let result = "";
                              // Scan up to 5 steps ahead to find the matching result, skipping garbage
                              for (let j = i + 1; j < Math.min(i + 6, combinedSteps.length); j++) {
                                if (consumedIndices.has(j)) continue;
                                const nextStep = combinedSteps[j];
                                if (!nextStep) continue;

                                // If we hit another TOOL_CALL, stop scanning (current call has no result?)
                                if (nextStep.type === 'thought' && nextStep.data.thought.includes('TOOL_CALL:')) {
                                  break;
                                }

                                if (nextStep.type === 'thought' && nextStep.data.thought.includes('TOOL_RESULT:')) {
                                  // Found result!
                                  const resultContent = nextStep.data.thought;
                                  result = resultContent.replace(/.*TOOL_RESULT:\s*/, '').trim();
                                  consumedIndices.add(j); // Mark as consumed
                                  break;
                                }
                              }

                              finalSteps.push({
                                type: 'synthetic_tool',
                                data: {
                                  id: `synthetic-${step.data.step_index}`,
                                  name,
                                  args,
                                  result,
                                  agent: step.data.agent
                                },
                                sortKey: step.sortKey
                              });
                            } else {
                              // Normal thought
                              finalSteps.push(step);
                            }
                          } else {
                            // Tool call
                            finalSteps.push(step);
                          }
                        }

                        return finalSteps.map((step, displayIndex) => {
                          if (step.type === 'thought') {
                            return (
                              <ThoughtBox
                                key={`thought-${step.data.step_index}-${displayIndex}`}
                                thought={step.data.thought}
                                stepNumber={displayIndex + 1}
                                totalSteps={totalSteps}
                                defaultExpanded={true}
                              />
                            );
                          } else if (step.type === 'synthetic_tool') {
                            return (
                              <StepBox
                                key={step.data.id}
                                toolCall={step.data}
                                stepNumber={displayIndex + 1}
                                totalSteps={ongoing ? undefined : totalSteps}
                                agent={step.data.agent}
                                defaultExpanded={false} // Internal steps collapsed by default
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
                                defaultExpanded={true} // Main PM Agent box expanded
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

          {/* Report/Insights Section */}
          {(hasReport || isGeneratingReport) && (
            <div className={cn((toolCalls.length > 0 || thoughts.length > 0) ? "border-t pt-4" : "", "break-words [word-break:break-word] [overflow-wrap:anywhere]")}>
              <div className="flex items-center gap-2 mb-3">
                <Sparkles size={16} className="text-[#FE5000]" />
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
