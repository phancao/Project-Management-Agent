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
  list_projects: <FolderKanban size={16} />,
  get_project: <FolderKanban size={16} />,
  create_project: <FolderKanban size={16} />,
  project_health: <BarChart3 size={16} />,
  
  // Task tools
  list_tasks: <ListTodo size={16} />,
  get_task: <ListTodo size={16} />,
  create_task: <ListTodo size={16} />,
  update_task: <ListTodo size={16} />,
  
  // Sprint tools
  list_sprints: <GitBranch size={16} />,
  get_sprint: <GitBranch size={16} />,
  sprint_report: <BarChart3 size={16} />,
  burndown_chart: <BarChart3 size={16} />,
  velocity_chart: <BarChart3 size={16} />,
  
  // User tools
  list_users: <Users size={16} />,
  get_user: <Users size={16} />,
  
  // Default
  default: <Wrench size={16} />,
};

// Get friendly name for tool
function getToolDisplayName(toolName: string): string {
  const nameMap: Record<string, string> = {
    list_projects: "List Projects",
    get_project: "Get Project",
    create_project: "Create Project",
    project_health: "Project Health",
    list_tasks: "List Tasks",
    get_task: "Get Task",
    create_task: "Create Task",
    update_task: "Update Task",
    list_sprints: "List Sprints",
    get_sprint: "Get Sprint",
    sprint_report: "Sprint Report",
    burndown_chart: "Burndown Chart",
    velocity_chart: "Velocity Chart",
    list_users: "List Users",
    get_user: "Get User",
    web_search: "Web Search",
    crawl_tool: "Read Page",
    python_repl_tool: "Run Python",
  };
  return nameMap[toolName] || toolName.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

// Parse result to get summary
function getResultSummary(toolName: string, result: string | undefined): string {
  if (!result) return "Running...";
  
  try {
    const parsed = parseJSON(result, null);
    
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
    
    if (parsed.total !== undefined) {
      return `Found ${parsed.total} item${parsed.total !== 1 ? "s" : ""}`;
    }
    
    if (parsed.sprints) {
      return `Found ${parsed.sprints.length} sprint${parsed.sprints.length !== 1 ? "s" : ""}`;
    }
    
    if (parsed.tasks) {
      return `Found ${parsed.tasks.length} task${parsed.tasks.length !== 1 ? "s" : ""}`;
    }
    
    if (parsed.projects) {
      return `Found ${parsed.projects.length} project${parsed.projects.length !== 1 ? "s" : ""}`;
    }
    
    if (parsed.name) {
      return parsed.name;
    }
    
    if (parsed.title) {
      return parsed.title;
    }
    
    if (parsed.message) {
      return parsed.message;
    }
    
    if (parsed.error) {
      return `Error: ${parsed.error}`;
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
}

export function StepBox({ 
  toolCall, 
  stepNumber, 
  totalSteps,
  className,
  defaultExpanded = false 
}: StepBoxProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const { resolvedTheme } = useTheme();
  
  const isRunning = toolCall.result === undefined;
  const hasError = toolCall.result?.startsWith("Error") || 
                   toolCall.result?.includes('"error"');
  
  const icon = TOOL_ICONS[toolCall.name] || TOOL_ICONS.default;
  const displayName = getToolDisplayName(toolCall.name);
  const summary = getResultSummary(toolCall.name, toolCall.result);
  
  // Parse args for display
  const argsDisplay = useMemo(() => {
    if (!toolCall.args) return null;
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
    >
      <Card 
        className={cn(
          "overflow-hidden transition-all duration-200",
          isRunning && "border-blue-500/50 bg-blue-50/50 dark:bg-blue-950/20",
          hasError && "border-red-500/50 bg-red-50/50 dark:bg-red-950/20",
          !isRunning && !hasError && "border-green-500/30 bg-green-50/30 dark:bg-green-950/10"
        )}
      >
        {/* Header - always visible */}
        <button
          className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-accent/50 transition-colors"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          {/* Status icon */}
          <div className="flex-shrink-0">
            {isRunning ? (
              <Loader2 size={18} className="animate-spin text-blue-500" />
            ) : hasError ? (
              <AlertCircle size={18} className="text-red-500" />
            ) : (
              <CheckCircle2 size={18} className="text-green-500" />
            )}
          </div>
          
          {/* Tool icon and name */}
          <div className="flex items-center gap-2 flex-shrink-0 text-muted-foreground">
            {icon}
            <span className="font-medium text-sm">{displayName}</span>
          </div>
          
          {/* Step number */}
          {stepNumber !== undefined && totalSteps !== undefined && (
            <span className="text-xs text-muted-foreground bg-accent px-2 py-0.5 rounded-full">
              {stepNumber}/{totalSteps}
            </span>
          )}
          
          {/* Summary */}
          <span className="flex-grow text-sm text-muted-foreground truncate">
            {summary}
          </span>
          
          {/* Expand icon */}
          <div className="flex-shrink-0 text-muted-foreground">
            {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
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
    <div className={cn("flex flex-col gap-2", className)}>
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

