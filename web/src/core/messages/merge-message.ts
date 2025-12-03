// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import type {
  ChatEvent,
  InterruptEvent,
  MessageChunkEvent,
  ToolCallChunksEvent,
  ToolCallResultEvent,
  ToolCallsEvent,
} from "../api";
import { deepClone } from "../utils/deep-clone";

import type { Message } from "./types";

export function mergeMessage(message: Message, event: ChatEvent) {
  if (event.type === "message_chunk") {
    mergeTextMessage(message, event);
  } else if (event.type === "tool_calls" || event.type === "tool_call_chunks") {
    mergeToolCallMessage(message, event);
  } else if (event.type === "tool_call_result") {
    mergeToolCallResultMessage(message, event);
  } else if (event.type === "interrupt") {
    mergeInterruptMessage(message, event);
  } else if (event.type === "step_progress") {
    mergeStepProgressMessage(message, event);
  }
  if (event.data.finish_reason) {
    message.finishReason = event.data.finish_reason;
    message.isStreaming = false;
    if (message.toolCalls) {
      message.toolCalls.forEach((toolCall) => {
        if (toolCall.argsChunks?.length) {
          const argsString = toolCall.argsChunks?.join("") ?? "";
          try {
            toolCall.args = JSON.parse(argsString);
          } catch {
            // Try to extract valid JSON if there are extra characters
            try {
              // Find the first { or [ and the matching closing bracket
              const startBrace = argsString.indexOf("{");
              const startBracket = argsString.indexOf("[");
              let start = -1;
              let endChar = "";
              
              if (startBrace >= 0 && (startBracket < 0 || startBrace < startBracket)) {
                start = startBrace;
                endChar = "}";
              } else if (startBracket >= 0) {
                start = startBracket;
                endChar = "]";
              }
              
              if (start >= 0) {
                // Find matching end by counting braces/brackets
                let depth = 0;
                let inString = false;
                let escapeNext = false;
                let end = -1;
                
                for (let i = start; i < argsString.length; i++) {
                  const char = argsString[i];
                  
                  if (escapeNext) {
                    escapeNext = false;
                    continue;
                  }
                  
                  if (char === "\\") {
                    escapeNext = true;
                    continue;
                  }
                  
                  if (char === '"') {
                    inString = !inString;
                    continue;
                  }
                  
                  if (inString) continue;
                  
                  if (char === "{" || char === "[") {
                    depth++;
                  } else if (char === "}" || char === "]") {
                    depth--;
                    if (depth === 0) {
                      end = i;
                      break;
                    }
                  }
                }
                
                if (end > start) {
                  const extracted = argsString.substring(start, end + 1);
                  toolCall.args = JSON.parse(extracted);
                } else {
                  console.warn(`[mergeMessage] Failed to extract valid JSON from argsChunks: ${argsString.substring(0, 100)}...`);
                  toolCall.args = {};
                }
              } else {
                console.warn(`[mergeMessage] No JSON structure found in argsChunks: ${argsString.substring(0, 100)}...`);
                toolCall.args = {};
              }
            } catch (extractError) {
              console.warn(`[mergeMessage] Failed to parse tool call args: ${argsString.substring(0, 100)}...`, extractError);
              toolCall.args = {};
            }
          }
          delete toolCall.argsChunks;
        }
      });
    }
  }
  return deepClone(message);
}

function mergeTextMessage(message: Message, event: MessageChunkEvent) {
  if (event.data.content) {
    // Ensure content is initialized as string (not undefined/null)
    message.content = (message.content ?? "") + event.data.content;
    // Ensure contentChunks is initialized
    message.contentChunks = message.contentChunks ?? [];
    message.contentChunks.push(event.data.content);
  }
  if (event.data.reasoning_content) {
    message.reasoningContent = (message.reasoningContent ?? "") + event.data.reasoning_content;
    message.reasoningContentChunks = message.reasoningContentChunks ?? [];
    message.reasoningContentChunks.push(event.data.reasoning_content);
  }
}
function convertToolChunkArgs(args: string) {
  // Convert escaped characters in args
  if (!args) return "";
  return args.replace(/&#91;/g, "[").replace(/&#93;/g, "]").replace(/&#123;/g, "{").replace(/&#125;/g, "}");
}
function mergeToolCallMessage(
  message: Message,
  event: ToolCallsEvent | ToolCallChunksEvent,
) {
  // Initialize toolCalls array if not present
  message.toolCalls ??= [];
  
  if (event.type === "tool_calls" && event.data.tool_calls?.length) {
    // MERGE tool calls instead of replacing - backend may send multiple tool_calls events
    // for parallel tool calls
    for (const raw of event.data.tool_calls) {
      if (!raw.name || !raw.id) continue; // Skip tool calls without names or IDs
      
      // Check if this tool call already exists (by ID)
      const existingIndex = message.toolCalls.findIndex(tc => tc.id === raw.id);
      if (existingIndex >= 0) {
        // Update existing tool call
        const existing = message.toolCalls[existingIndex]!;
        message.toolCalls[existingIndex] = {
          id: existing.id,
          name: raw.name,
          args: raw.args,
          argsChunks: existing.argsChunks,
          result: existing.result,
        };
      } else {
        // Add new tool call
        message.toolCalls.push({
      id: raw.id,
      name: raw.name,
      args: raw.args,
      result: undefined,
        });
      }
    }
  }

  for (const chunk of event.data.tool_call_chunks) {
    if (chunk.id) {
      const toolCall = message.toolCalls.find(
        (toolCall) => toolCall.id === chunk.id,
      );
      if (toolCall) {
        toolCall.argsChunks = [convertToolChunkArgs(chunk.args)];
      }
    } else {
      const streamingToolCall = message.toolCalls.find(
        (toolCall) => toolCall.argsChunks?.length,
      );
      if (streamingToolCall) {
        streamingToolCall.argsChunks!.push(convertToolChunkArgs(chunk.args));
      }
    }
  }
}

function mergeToolCallResultMessage(
  message: Message,
  event: ToolCallResultEvent,
) {
  const toolCall = message.toolCalls?.find(
    (toolCall) => toolCall.id === event.data.tool_call_id,
  );
  if (toolCall) {
    // Ensure result is always a string (not undefined/null)
    toolCall.result = event.data.content ?? "";
    console.log(`[ToolCallResult] Set result for ${toolCall.name}: ${toolCall.result?.substring(0, 50)}...`);
  } else {
    console.warn(`[ToolCallResult] Could not find tool call with id=${event.data.tool_call_id}`);
  }
}

function mergeInterruptMessage(message: Message, event: InterruptEvent) {
  message.isStreaming = false;
  message.options = event.data.options;
}

function mergeStepProgressMessage(message: Message, event: import("../api").StepProgressEvent) {
  message.currentStep = event.data.step_title;
  message.currentStepDescription = event.data.step_description;
  message.currentStepIndex = event.data.step_index;
  message.totalSteps = event.data.total_steps;
}
