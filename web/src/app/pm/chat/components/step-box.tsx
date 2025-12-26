// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

/**
 * StepBox Component
 * 
 * Displays individual tool call steps inline in the chat.
 * Shows tool name, status, and result in a collapsible card.
 * Updated with Brand Colors.
 */

import { motion } from "framer-motion";
import {
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  AlertCircle,
  Loader2,
  Wrench,
  FolderKanban,
  BarChart3,
  ListTodo,
  GitBranch,
  Users,
  Brain
} from "lucide-react";
import React, { useMemo, useState } from "react";
import { useTheme } from "next-themes";
import SyntaxHighlighter from "react-syntax-highlighter";
import { docco } from "react-syntax-highlighter/dist/esm/styles/hljs";
import { dark } from "react-syntax-highlighter/dist/esm/styles/prism";

import { Card } from "~/components/ui/card";
import type { ToolCallRuntime } from "~/core/messages";
import { cn } from "~/lib/utils";
import { parseJSON } from "~/core/utils";

// Tool category icons
const TOOL_ICONS: Record<string, React.ReactNode> = {
  // Project tools
  list_projects: <FolderKanban size={12} />,
  get_project: <FolderKanban size={12} />,
  create_project: <FolderKanban size={12} />,
  project_health: <BarChart3 size={12} />,

  // Task tools
  list_tasks: <ListTodo size={12} />,
  list_tasks_by_assignee: <ListTodo size={12} />,
  list_tasks_in_sprint: <ListTodo size={12} />,
  list_unassigned_tasks: <ListTodo size={12} />,
  get_task: <ListTodo size={12} />,
  create_task: <ListTodo size={12} />,
  update_task: <ListTodo size={12} />,

  // Sprint tools
  list_sprints: <GitBranch size={12} />,
  get_sprint: <GitBranch size={12} />,
  sprint_report: <BarChart3 size={12} />,
  burndown_chart: <BarChart3 size={12} />,
  velocity_chart: <BarChart3 size={12} />,
  cfd_chart: <BarChart3 size={12} />,
  cycle_time_chart: <BarChart3 size={12} />,
  work_distribution_chart: <BarChart3 size={12} />,
  issue_trend_chart: <BarChart3 size={12} />,

  // User tools
  list_users: <Users size={12} />,
  get_user: <Users size={12} />,

  // Cursor-style: Thought (reasoning)
  thought: <Brain size={12} />,

  // Default
  default: <Wrench size={12} />,
};

// Get friendly name for tool
function getToolDisplayName(toolName: string): string {
  const nameMap: Record<string, string> = {
    list_projects: "List Projects",
    get_project: "Get Project",
    create_project: "Create Project",
    project_health: "Project Health",
    list_tasks: "List Tasks",
    list_tasks_by_assignee: "List Tasks by Assignee",
    list_tasks_in_sprint: "List Tasks in Sprint",
    list_unassigned_tasks: "List Unassigned Tasks",
    get_task: "Get Task",
    create_task: "Create Task",
    update_task: "Update Task",
    list_sprints: "List Sprints",
    get_sprint: "Get Sprint",
    sprint_report: "Sprint Report",
    burndown_chart: "Burndown Chart",
    velocity_chart: "Velocity Chart",
    cfd_chart: "CFD Chart",
    cycle_time_chart: "Cycle Time Chart",
    work_distribution_chart: "Work Distribution Chart",
    issue_trend_chart: "Issue Trend Chart",
    list_users: "List Users",
    get_user: "Get User",
    web_search: "Web Search",
    crawl_tool: "Read Page",
    python_repl_tool: "Run Python",
    thought: "Thought",
    backend_api_call: "Internal API",
    get_current_project: "Get Current Project",
    optimize_context: "Optimize Context",
  };
  return nameMap[toolName] ?? toolName.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

// Get friendly name and color for agent
function getAgentDisplayInfo(agent?: string): { name: string; color: string; bgColor: string } {
  const agentMap: Record<string, { name: string; color: string; bgColor: string }> = {
    pm_agent: {
      name: "PM Agent",
      color: "text-[#162B75] dark:text-[#009CDF]",
      bgColor: "bg-[#162B75]/10 dark:bg-[#162B75]/30"
    },
    researcher: {
      name: "Researcher",
      color: "text-[#CE007C] dark:text-[#CE007C]",
      bgColor: "bg-[#CE007C]/10 dark:bg-[#CE007C]/30"
    },
    coder: {
      name: "Coder",
      color: "text-[#84BD00] dark:text-[#84BD00]",
      bgColor: "bg-[#84BD00]/10 dark:bg-[#84BD00]/30"
    },
    planner: {
      name: "Planner",
      color: "text-[#009682] dark:text-[#009682]",
      bgColor: "bg-[#009682]/10 dark:bg-[#009682]/30"
    },
    reporter: {
      name: "Reporter",
      color: "text-[#DA291C] dark:text-[#DA291C]",
      bgColor: "bg-[#DA291C]/10 dark:bg-[#DA291C]/30"
    },
  };

  if (agent && agent in agentMap) {
    return agentMap[agent]!;
  }

  // Default
  return {
    name: agent ? agent.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()) : "Agent",
    color: "text-gray-600 dark:text-gray-400",
    bgColor: "bg-gray-100 dark:bg-gray-900/30"
  };
}

// Parse result to get summary
function getResultSummary(toolName: string, result: string | undefined): string {
  if (!result) return "Running...";

  try {
    let parsed: unknown = null;
    try {
      parsed = parseJSON<unknown>(result, null);
    } catch (parseError) {
      console.debug(`[StepBox] Failed to parse result for ${toolName}:`, parseError);
      parsed = null;
    }

    if (parsed === null) {
      if (result.length > 100) return result.substring(0, 100) + "...";
      return result;
    }

    if (Array.isArray(parsed)) return `Found ${parsed.length} item${parsed.length !== 1 ? "s" : ""}`;

    if (typeof parsed === "object" && parsed !== null) {
      const obj = parsed as Record<string, unknown>;
      if (typeof obj.total === "number") return `Found ${obj.total} item${obj.total !== 1 ? "s" : ""}`;
      if (Array.isArray(obj.sprints)) return `Found ${obj.sprints.length} sprint${obj.sprints.length !== 1 ? "s" : ""}`;
      if (Array.isArray(obj.tasks)) return `Found ${obj.tasks.length} task${obj.tasks.length !== 1 ? "s" : ""}`;
      if (typeof obj.name === "string") return obj.name;
      if (typeof obj.title === "string") return obj.title;
      if (typeof obj.message === "string") return obj.message;
      if (typeof obj.error === "string") return `Error: ${obj.error}`;
    }

    return "Completed";
  } catch (error) {
    console.debug(`[StepBox] Error in getResultSummary for ${toolName}:`, error);
    return result.length > 100 ? result.substring(0, 100) + "..." : result;
  }
}

interface StepBoxProps {
  toolCall: ToolCallRuntime;
  stepNumber?: number;
  totalSteps?: number;
  className?: string;
  defaultExpanded?: boolean;
  agent?: string;
}

export function StepBox({
  toolCall,
  stepNumber,
  totalSteps,
  className,
  defaultExpanded = false,
  agent
}: StepBoxProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const { resolvedTheme } = useTheme();

  const isRunning = toolCall.result === undefined;
  const hasError = toolCall.result?.startsWith("Error") || toolCall.result?.includes('"error"');

  const icon = TOOL_ICONS[toolCall.name] ?? TOOL_ICONS.default;
  const displayName = getToolDisplayName(toolCall.name);
  const summary = getResultSummary(toolCall.name, toolCall.result);
  const agentInfo = getAgentDisplayInfo(agent);

  const argsDisplay = useMemo(() => {
    if (!toolCall.args) return null;
    if (typeof toolCall.args === 'string') return toolCall.args;
    const args = toolCall.args as Record<string, unknown>;
    const entries = Object.entries(args).filter(([_, v]) => v !== undefined && v !== null);
    if (entries.length === 0) return null;
    return entries.map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(", ");
  }, [toolCall.args]);

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
          // Brand Colors:
          // Running: Cyan #009CDF (White BG in light mode)
          isRunning && "border-[#009CDF]/50 bg-white dark:bg-[#009CDF]/20",
          // Error: Red #DA291C (White BG in light mode)
          hasError && "border-[#DA291C]/50 bg-white dark:bg-[#DA291C]/20",
          // Success: Green #84BD00 (White BG in light mode)
          !isRunning && !hasError && "border-[#84BD00]/30 bg-white dark:bg-[#84BD00]/10"
        )}
        style={{ minWidth: 0, maxWidth: '100%' }}
      >
        <button
          className="grid w-full grid-cols-[auto_auto_auto_auto_1fr_auto] items-center gap-1 px-2 py-0.5 text-left hover:bg-accent/50 transition-colors"
          style={{ minWidth: 0 }}
          onClick={() => setIsExpanded(!isExpanded)}
        >
          {/* Status icon */}
          <div className="shrink-0">
            {isRunning ? (
              <Loader2 size={12} className="animate-spin text-[#009CDF]" />
            ) : hasError ? (
              <AlertCircle size={12} className="text-[#DA291C]" />
            ) : (
              <CheckCircle2 size={12} className="text-[#84BD00]" />
            )}
          </div>

          {/* Tool icon and name */}
          <div className="flex items-center gap-1 shrink-0 text-foreground/80 dark:text-muted-foreground">
            {icon}
            <span className="font-medium text-xs">{displayName}</span>
          </div>

          {/* Step number */}
          {stepNumber !== undefined && (
            <span className="text-[10px] text-foreground/70 dark:text-muted-foreground bg-accent px-1.5 py-px rounded-full shrink-0">
              {totalSteps !== undefined ? `${stepNumber}/${totalSteps}` : `#${stepNumber}`}
            </span>
          )}

          {/* Agent badge */}
          {agent && (
            <span className={cn(
              "text-[10px] px-1.5 py-px rounded-full font-medium shrink-0",
              agentInfo.color,
              agentInfo.bgColor
            )}>
              {agentInfo.name}
            </span>
          )}

          {/* Summary */}
          <span className="text-xs text-foreground/90 dark:text-muted-foreground truncate min-w-0" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {summary}
          </span>

          {/* Expand icon */}
          <div className="shrink-0 text-muted-foreground">
            {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </div>
        </button>

        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="border-t"
          >
            {argsDisplay && (
              <div className="px-4 py-2 bg-accent/30">
                <div className="text-xs text-foreground/80 dark:text-muted-foreground font-mono">
                  {toolCall.name}({argsDisplay})
                </div>
              </div>
            )}

            {toolCall.result && (
              <div className="p-2 overflow-x-auto w-full font-mono text-xs [&_pre]:!whitespace-pre-wrap [&_pre]:!break-all [&_pre]:!w-full [&_pre]:!max-w-full [&_code]:!whitespace-pre-wrap [&_code]:!break-all" style={{ minWidth: 0, maxWidth: '100%' }}>
                <SyntaxHighlighter
                  language="json"
                  style={resolvedTheme === "dark" ? dark : docco}
                  customStyle={{
                    background: "transparent",
                    border: "none",
                    boxShadow: "none",
                    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                    fontSize: "inherit",
                    margin: 0,
                    padding: "8px",
                    maxWidth: "100%",
                    width: "100%",
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-all",
                  }}
                >
                  {formatResult(toolCall.result)}
                </SyntaxHighlighter>
              </div>
            )}

            {isRunning && (
              <div className="px-4 py-3 flex items-center gap-2 text-sm text-foreground/80 dark:text-muted-foreground">
                <Clock size={14} />
                <span>Waiting for response...</span>
              </div>
            )}
          </motion.div>
        )}
      </Card>
    </motion.div>
  );
}

function formatResult(result: string): string {
  try {
    const parsed = JSON.parse(result);
    return JSON.stringify(parsed, null, 2);
  } catch {
    return result;
  }
}

export function StepBoxList({ toolCalls, className }: { toolCalls: ToolCallRuntime[]; className?: string; }) {
  if (!toolCalls || toolCalls.length === 0) return null;
  return (
    <div className={cn("flex flex-col gap-0.5", className)}>
      {toolCalls.map((toolCall, index) => (
        <StepBox
          key={toolCall.id}
          toolCall={toolCall}
          stepNumber={index + 1}
          totalSteps={toolCalls.length}
        />
      ))}
    </div>
  );
}
