// Copyright (c) 2025
// SPDX-License-Identifier: MIT

/**
 * AnalysisBlock Component
 * 
 * Displays AI analysis results inline in the chat:
 * - Collapsible steps section showing tool calls
 * - Inline report/insights display (no modal needed)
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
import ReportEditor from "~/components/editor";
import { Button } from "~/components/ui/button";
import { Card, CardContent, CardHeader } from "~/components/ui/card";
import { Tooltip } from "~/components/deer-flow/tooltip";
import { useReplay } from "~/core/replay";
import { useMessage, useStore } from "~/core/store";
import { cn } from "~/lib/utils";
import { parseJSON } from "~/core/utils";

import { StepBox } from "./step-box";

interface AnalysisBlockProps {
  className?: string;
  researchId: string;
}

export function AnalysisBlock({ className, researchId }: AnalysisBlockProps) {
  const t = useTranslations("chat.research");
  const { isReplay } = useReplay();
  
  // Get research data from store - subscribe to messages map for real-time updates
  const reportId = useStore((state) => state.researchReportIds.get(researchId));
  const activityIds = useStore((state) => state.researchActivityIds.get(researchId)) ?? [];
  const planMessageId = useStore((state) => state.researchPlanIds.get(researchId));
  const ongoing = useStore((state) => state.ongoingResearchId === researchId);
  
  // Subscribe to the entire messages map to get real-time tool call updates
  const messages = useStore((state) => state.messages);
  
  const reportMessage = useMessage(reportId ?? "");
  const planMessage = useMessage(planMessageId ?? "");
  
  const hasReport = reportId !== undefined && reportMessage?.content;
  const isGeneratingReport = reportMessage?.isStreaming ?? false;
  
  // Get title from plan
  const title = useMemo(() => {
    if (planMessage?.content) {
      return parseJSON(planMessage.content, { title: "" }).title || "AI Analysis";
    }
    return "AI Analysis";
  }, [planMessage?.content]);
  
  // Collect all tool calls from activities - now reactive to messages changes
  const toolCalls = useMemo(() => {
    const calls: Array<{ id: string; name: string; args: unknown; result?: string }> = [];
    
    for (const activityId of activityIds) {
      const message = messages.get(activityId);
      if (message?.toolCalls) {
        for (const tc of message.toolCalls) {
          // Skip error results
          if (typeof tc.result === "string" && tc.result.startsWith("Error")) {
            continue;
          }
          calls.push(tc);
        }
      }
    }
    
    return calls;
  }, [activityIds, messages]);
  
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
    >
      <Card className="overflow-hidden">
        {/* Header */}
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-gradient-to-br from-purple-500/20 to-blue-500/20">
                <Brain size={20} className="text-purple-600 dark:text-purple-400" />
              </div>
              <div>
                <RainbowText 
                  className="text-lg font-semibold"
                  animated={ongoing || isGeneratingReport}
                >
                  {title}
                </RainbowText>
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
        
        <CardContent className="pt-0">
          {/* Steps Section - Collapsible */}
          {toolCalls.length > 0 && (
            <div className="mb-4">
              <button
                className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors w-full py-2"
                onClick={() => setStepsExpanded(!stepsExpanded)}
              >
                {stepsExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                <span className="font-medium">Steps</span>
                <span className="text-xs bg-accent px-2 py-0.5 rounded-full">
                  {toolCalls.length}
                </span>
              </button>
              
              <AnimatePresence>
                {stepsExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    <div className="flex flex-col gap-0.5 pt-0.5">
                      {toolCalls.map((toolCall, index) => (
                        <StepBox
                          key={toolCall.id}
                          toolCall={toolCall}
                          stepNumber={index + 1}
                          totalSteps={toolCalls.length}
                        />
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}
          
          {/* Loading indicator when no tool calls yet */}
          {toolCalls.length === 0 && ongoing && (
            <div className="py-4">
              <LoadingAnimation />
            </div>
          )}
          
          {/* Report/Insights Section - Inline */}
          {(hasReport || isGeneratingReport) && (
            <div className="border-t pt-4">
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
                <div className="prose prose-sm dark:prose-invert max-w-none break-words [word-break:break-word]">
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

