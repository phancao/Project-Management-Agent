// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

export type MessageRole = "user" | "assistant" | "tool";

export interface Message {
  id: string;
  threadId: string;
  agent?:
  | "coordinator"
  | "planner"
  | "researcher"
  | "coder"
  | "reporter"
  | "podcast"
  | "pm_agent"
  | "react_agent";  // NEW: ReAct agent (fast path)
  role: MessageRole;
  isStreaming?: boolean;
  content: string;
  contentChunks: string[];
  reasoningContent?: string;
  reasoningContentChunks?: string[];
  toolCalls?: ToolCallRuntime[];
  options?: Option[];
  finishReason?: "stop" | "interrupt" | "tool_calls";
  interruptFeedback?: string;
  resources?: Array<Resource>;
  // Step progress fields
  currentStep?: string;
  currentStepDescription?: string;
  currentStepIndex?: number;
  totalSteps?: number;
  // Cursor-style: Thoughts from ReAct agent
  reactThoughts?: Array<{
    thought: string;
    before_tool: boolean;
    step_index: number;
  }>;
}

export interface Option {
  text: string;
  value: string;
}

export interface ToolCallRuntime {
  id: string;
  name: string;
  args: Record<string, unknown>;
  argsChunks?: string[];
  result?: string;
}

export interface Resource {
  uri: string;
  title: string;
}
