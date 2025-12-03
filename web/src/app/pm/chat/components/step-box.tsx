// Copyright (c) 2025
// SPDX-License-Identifier: MIT

/**
 * StepBox Component
 * 
 * Displays individual tool call steps inline in the chat.
 * Shows tool name, status, and result in a collapsible card.
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
  Database,
  BarChart3,
  ListTodo,
  FolderKanban,
  Users,
  GitBranch
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
  };
  return nameMap[toolName] ?? toolName.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

// Get friendly name and color for agent
function getAgentDisplayInfo(agent?: string): { name: string; color: string; bgColor: string } {
  const agentMap: Record<string, { name: string; color: string; bgColor: string }> = {
    pm_agent: { 
      name: "PM Agent", 
      color: "text-blue-600 dark:text-blue-400", 
      bgColor: "bg-blue-100 dark:bg-blue-900/30" 
    },
    researcher: { 
      name: "Researcher", 
      color: "text-purple-600 dark:text-purple-400", 
      bgColor: "bg-purple-100 dark:bg-purple-900/30" 
    },
    coder: { 
      name: "Coder", 
      color: "text-green-600 dark:text-green-400", 
      bgColor: "bg-green-100 dark:bg-green-900/30" 
    },
    planner: { 
      name: "Planner", 
      color: "text-orange-600 dark:text-orange-400", 
      bgColor: "bg-orange-100 dark:bg-orange-900/30" 
    },
    reporter: { 
      name: "Reporter", 
      color: "text-amber-600 dark:text-amber-400", 
      bgColor: "bg-amber-100 dark:bg-amber-900/30" 
    },
  };
  
  if (agent && agent in agentMap) {
    return agentMap[agent]!;
  }
  
  // Default for unknown agents
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
    const parsed = parseJSON<unknown>(result, null);
    
    if (parsed === null) {
      // Plain text result
      if (result.length > 100) {
        return result.substring(0, 100) + "...";
      }
      return result;
    }
    
    // Handle different result structures
    if (Array.isArray(parsed)) {
      return `Found ${parsed.length} item${parsed.length !== 1 ? "s" : ""}`;
    }
    
    if (typeof parsed === "object" && parsed !== null) {
      const obj = parsed as Record<string, unknown>;
      
      if (typeof obj.total === "number") {
        return `Found ${obj.total} item${obj.total !== 1 ? "s" : ""}`;
      }
      
      if (Array.isArray(obj.sprints)) {
        return `Found ${obj.sprints.length} sprint${obj.sprints.length !== 1 ? "s" : ""}`;
      }
      
      if (Array.isArray(obj.tasks)) {
        return `Found ${obj.tasks.length} task${obj.tasks.length !== 1 ? "s" : ""}`;
      }
      
      if (Array.isArray(obj.projects)) {
        return `Found ${obj.projects.length} project${obj.projects.length !== 1 ? "s" : ""}`;
      }
      
      if (typeof obj.name === "string") {
        return obj.name;
      }
      
      if (typeof obj.title === "string") {
        return obj.title;
      }
      
      if (typeof obj.message === "string") {
        return obj.message;
      }
      
      if (typeof obj.error === "string") {
        return `Error: ${obj.error}`;
      }
    }
    
    return "Completed";
  } catch {
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
  const hasError = toolCall.result?.startsWith("Error") || 
                   toolCall.result?.includes('"error"');
  
  const icon = TOOL_ICONS[toolCall.name] ?? TOOL_ICONS.default;
  const displayName = getToolDisplayName(toolCall.name);
  const summary = getResultSummary(toolCall.name, toolCall.result);
  const agentInfo = getAgentDisplayInfo(agent);
  
  // Parse args for display
  const argsDisplay = useMemo(() => {
    if (!toolCall.args) return null;
    const args = toolCall.args;
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
    >
      <Card 
        className={cn(
          "overflow-hidden transition-all duration-200 py-0 gap-0",
          isRunning && "border-blue-500/50 bg-blue-50/50 dark:bg-blue-950/20",
          hasError && "border-red-500/50 bg-red-50/50 dark:bg-red-950/20",
          !isRunning && !hasError && "border-green-500/30 bg-green-50/30 dark:bg-green-950/10"
        )}
      >
        {/* Header - always visible */}
        <button
          className="flex w-full items-center gap-1 px-2 py-0.5 text-left hover:bg-accent/50 transition-colors"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          {/* Status icon */}
          <div className="shrink-0">
            {isRunning ? (
              <Loader2 size={12} className="animate-spin text-blue-500" />
            ) : hasError ? (
              <AlertCircle size={12} className="text-red-500" />
            ) : (
              <CheckCircle2 size={12} className="text-green-500" />
            )}
          </div>
          
          {/* Tool icon and name */}
          <div className="flex items-center gap-1 shrink-0 text-muted-foreground">
            {icon}
            <span className="font-medium text-xs">{displayName}</span>
          </div>
          
          {/* Step number */}
          {stepNumber !== undefined && (
            <span className="text-[10px] text-muted-foreground bg-accent px-1.5 py-px rounded-full">
              {totalSteps !== undefined ? `${stepNumber}/${totalSteps}` : `#${stepNumber}`}
            </span>
          )}
          
          {/* Agent badge */}
          {agent && (
            <span className={cn(
              "text-[10px] px-1.5 py-px rounded-full font-medium",
              agentInfo.color,
              agentInfo.bgColor
            )}>
              {agentInfo.name}
            </span>
          )}
          
          {/* Summary */}
          <span className="grow text-xs text-muted-foreground truncate">
            {summary}
          </span>
          
          {/* Expand icon */}
          <div className="shrink-0 text-muted-foreground">
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
            className="border-t"
          >
            {/* Arguments */}
            {argsDisplay && (
              <div className="px-4 py-2 bg-accent/30">
                <div className="text-xs text-muted-foreground font-mono">
                  {toolCall.name}({argsDisplay})
                </div>
              </div>
            )}
            
            {/* Result */}
            {toolCall.result && (
              <div className="p-2 max-h-[300px] overflow-auto">
                <SyntaxHighlighter
                  language="json"
                  style={resolvedTheme === "dark" ? dark : docco}
                  customStyle={{
                    background: "transparent",
                    border: "none",
                    boxShadow: "none",
                    fontSize: "12px",
                    margin: 0,
                    padding: "8px",
                  }}
                  wrapLongLines
                >
                  {formatResult(toolCall.result)}
                </SyntaxHighlighter>
              </div>
            )}
            
            {/* Loading state */}
            {isRunning && (
              <div className="px-4 py-3 flex items-center gap-2 text-sm text-muted-foreground">
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

// Format result for display
function formatResult(result: string): string {
  try {
    const parsed = JSON.parse(result);
    return JSON.stringify(parsed, null, 2);
  } catch {
    return result;
  }
}

/**
 * StepBoxList - Renders a list of tool calls as StepBoxes
 */
interface StepBoxListProps {
  toolCalls: ToolCallRuntime[];
  className?: string;
}

export function StepBoxList({ toolCalls, className }: StepBoxListProps) {
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

