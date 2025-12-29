// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import type {
  ChatEvent,
  InterruptEvent,
  MessageChunkEvent,
  ThoughtsEvent,
  ToolCallChunksEvent,
  ToolCallResultEvent,
  ToolCallsEvent,
} from "../api";
import { deepClone } from "../utils/deep-clone";

import type { Message } from "./types";

export function mergeMessage(message: Message, event: ChatEvent) {
  const mergeTimestamp = new Date().toISOString();
  console.log(`[mergeMessage] 🚪 [${mergeTimestamp}] ENTRY: messageId=${message.id}, agent=${message.agent}, eventType=${event.type}`);

  // DEBUG: Log function entry for reporter messages
  if (message.agent === "reporter") {
    const contentBefore = message.content?.length ?? 0;
    const chunksBefore = message.contentChunks?.length ?? 0;
    const lastCharsBefore = message.content?.slice(-50) ?? "";
    console.log(`[DEBUG-MERGE-ENTRY] 🚪 mergeMessage ENTRY: messageId=${message.id}, eventType=${event.type}, contentLen=${contentBefore}, chunksLen=${chunksBefore}`);
    if (contentBefore > 0) {
      console.log(`[DEBUG-MERGE-ENTRY] 📝 Last 50 chars: "${lastCharsBefore}"`);
    }
    console.trace(`[DEBUG-MERGE-ENTRY] Stack trace for mergeMessage entry`);
  }

  if (event.type === "message_chunk") {
    mergeTextMessage(message, event);
  } else if (event.type === "tool_calls" || event.type === "tool_call_chunks") {
    console.log(`[mergeMessage] 🔧 [${mergeTimestamp}] Routing to mergeToolCallMessage: messageId=${message.id}, eventType=${event.type}`);
    mergeToolCallMessage(message, event);
  } else if (event.type === "thoughts") {
    mergeThoughtsMessage(message, event);
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

  // DEBUG: Log function exit for reporter messages
  if (message.agent === "reporter") {
    const contentAfter = message.content?.length ?? 0;
    const chunksAfter = message.contentChunks?.length ?? 0;
    const lastCharsAfter = message.content?.slice(-50) ?? "";
    console.log(`[DEBUG-MERGE-EXIT] 🚪 mergeMessage EXIT: messageId=${message.id}, contentLen=${contentAfter}, chunksLen=${chunksAfter}, finishReason=${message.finishReason}`);
    if (contentAfter > 0) {
      console.log(`[DEBUG-MERGE-EXIT] 📝 Last 50 chars: "${lastCharsAfter}"`);
    }
  }

  return deepClone(message);
}

function mergeTextMessage(message: Message, event: MessageChunkEvent) {
  // DEBUG: Log function entry for reporter messages
  if (message.agent === "reporter") {
    const contentBefore = message.content?.length ?? 0;
    const chunksBefore = message.contentChunks?.length ?? 0;
    const lastCharsBefore = message.content?.slice(-50) ?? "";
    console.log(`[DEBUG-MERGE-TEXT-ENTRY] 🚪 mergeTextMessage ENTRY: messageId=${message.id}, contentLen=${contentBefore}, chunksLen=${chunksBefore}, eventContentLen=${event.data.content?.length ?? 0}`);
    if (contentBefore > 0) {
      console.log(`[DEBUG-MERGE-TEXT-ENTRY] 📝 Last 50 chars before: "${lastCharsBefore}"`);
    }
    console.trace(`[DEBUG-MERGE-TEXT-ENTRY] Stack trace for mergeTextMessage entry`);
  }

  if (event.data.content) {
    const contentBefore = message.content?.length ?? 0;
    const chunksBefore = message.contentChunks?.length ?? 0;
    const lastCharsBefore = message.content?.slice(-50) ?? "";

    // Ensure content is initialized as string (not undefined/null)
    message.content = (message.content ?? "") + event.data.content;
    // Ensure contentChunks is initialized
    message.contentChunks = message.contentChunks ?? [];
    message.contentChunks.push(event.data.content);

    // DEBUG: Log for reporter messages
    if (message.agent === "reporter") {
      const contentAfter = message.content?.length ?? 0;
      const chunksAfter = message.contentChunks?.length ?? 0;
      const lastCharsAfter = message.content?.slice(-50) ?? "";
      console.log(`[DEBUG-MERGE-TEXT] 📝 mergeTextMessage: messageId=${message.id}, contentBefore=${contentBefore}→${contentAfter}, chunksBefore=${chunksBefore}→${chunksAfter}, chunkLen=${event.data.content.length}`);
      if (contentBefore > 0) {
        console.log(`[DEBUG-MERGE-TEXT] 📝 Last 50 chars before: "${lastCharsBefore}"`);
      }
      console.log(`[DEBUG-MERGE-TEXT] 📝 Last 50 chars after: "${lastCharsAfter}"`);
      console.log(`[DEBUG-MERGE-TEXT] 📝 New chunk: "${event.data.content.substring(0, 50)}${event.data.content.length > 50 ? '...' : ''}"`);

      // Check for content loss
      if (contentBefore > 0 && contentAfter === 0) {
        console.error(`[DEBUG-MERGE-TEXT] ❌ CONTENT LOST in mergeTextMessage! messageId=${message.id}, before=${contentBefore}, after=${contentAfter}`);
        console.trace("Stack trace for content loss in mergeTextMessage");
      }
    }
  }

  // DEBUG: Log function exit for reporter messages
  if (message.agent === "reporter") {
    const contentAfter = message.content?.length ?? 0;
    const chunksAfter = message.contentChunks?.length ?? 0;
    const lastCharsAfter = message.content?.slice(-50) ?? "";
    console.log(`[DEBUG-MERGE-TEXT-EXIT] 🚪 mergeTextMessage EXIT: messageId=${message.id}, contentLen=${contentAfter}, chunksLen=${chunksAfter}`);
    if (contentAfter > 0) {
      console.log(`[DEBUG-MERGE-TEXT-EXIT] 📝 Last 50 chars: "${lastCharsAfter}"`);
    }
  }
  if (event.data.reasoning_content) {
    message.reasoningContent = (message.reasoningContent ?? "") + event.data.reasoning_content;
    message.reasoningContentChunks = message.reasoningContentChunks ?? [];
    message.reasoningContentChunks.push(event.data.reasoning_content);
  }
  // Add react_thoughts if available
  if (event.data.react_thoughts) {
    message.reactThoughts = event.data.react_thoughts.map(t => ({
      ...t,
      before_tool: t.before_tool ?? false,
    }));
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
  const mergeToolCallTimestamp = new Date().toISOString();
  console.log(`[mergeToolCallMessage] 🔧 [${mergeToolCallTimestamp}] Called: messageId=${message.id}, agent=${message.agent}, eventType=${event.type}`, {
    hasReactThoughts: !!(event.data as any).react_thoughts,
    reactThoughtsCount: (event.data as any).react_thoughts?.length ?? 0,
    toolCallsCount: (event.data as any).tool_calls?.length ?? 0,
    eventDataKeys: Object.keys(event.data),
  });

  // Initialize toolCalls array if not present
  message.toolCalls ??= [];

  // Extract react_thoughts from tool_calls event if present
  const data = event.data as any;
  if (data.react_thoughts) {
    const thoughtTimestamp = new Date().toISOString();
    console.log(`[mergeToolCallMessage] 💭 [${thoughtTimestamp}] Found react_thoughts: count=${data.react_thoughts.length}`, {
      thoughts: data.react_thoughts.map((t: any) => ({ step_index: t.step_index, thought: t.thought?.substring(0, 50) })),
    });
    message.reactThoughts = data.react_thoughts.map((t: any) => ({
      ...t,
      before_tool: t.before_tool ?? false,
    }));
  }

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

  // Safely handle tool_call_chunks - may be undefined or not an array
  if (event.data.tool_call_chunks && Array.isArray(event.data.tool_call_chunks)) {
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
}

function mergeThoughtsMessage(
  message: Message,
  event: ThoughtsEvent,
) {
  const mergeThoughtsTimestamp = new Date().toISOString();
  console.log(`[mergeThoughtsMessage] 💭 [${mergeThoughtsTimestamp}] Called: messageId=${message.id}, agent=${message.agent}, count=${event.data.react_thoughts?.length ?? 0}`);

  // Merge thoughts instead of replace to handle incremental updates
  const existingThoughts = message.reactThoughts ?? [];
  const thoughtsMap = new Map<string, typeof existingThoughts[0]>();

  // Add existing thoughts to map (keyed by step_index + thought content)
  existingThoughts.forEach(thought => {
    const key = `${thought.step_index}:${thought.thought}`;
    thoughtsMap.set(key, thought);
  });

  // Add new thoughts from event
  if (event.data.react_thoughts) {
    event.data.react_thoughts.forEach((thought) => {
      const key = `${thought.step_index}:${thought.thought}`;
      if (!thoughtsMap.has(key)) {
        thoughtsMap.set(key, {
          thought: thought.thought,
          before_tool: thought.before_tool ?? false,
          step_index: thought.step_index,
        });
      }
    });
  }

  // Convert map back to array and sort by step_index
  message.reactThoughts = Array.from(thoughtsMap.values()).sort((a, b) => a.step_index - b.step_index);

  console.log(`[mergeThoughtsMessage] 💭 [${mergeThoughtsTimestamp}] Merged thoughts: messageId=${message.id}, totalCount=${message.reactThoughts.length}`);
}

function mergeToolCallResultMessage(
  message: Message,
  event: ToolCallResultEvent,
) {
  // [TOOL-RESULT-DEBUG] Step 10: Log ID matching in merge logic
  const ts = new Date().toISOString().slice(11, 23);
  const eventToolCallId = event.data.tool_call_id;
  const eventToolName = (event.data as any).agent ?? (event.data as any).name ?? "";
  const existingToolCallIds = message.toolCalls?.map(t => t.id) ?? [];
  const existingToolCallNames = message.toolCalls?.map(t => t.name) ?? [];
  console.log(`[TOOL-RESULT-DEBUG][${ts}][merge-message.ts:merge] Looking for tool_call_id="${eventToolCallId}" (name="${eventToolName}") in message.toolCalls:`, existingToolCallIds);

  // Primary match: exact tool_call_id match
  let toolCall = message.toolCalls?.find(
    (toolCall) => toolCall.id === event.data.tool_call_id,
  );

  // Fallback match: if no ID match and we have a tool name, match by name
  // This handles inner tool calls whose IDs don't match the registered IDs
  if (!toolCall && eventToolName && message.toolCalls) {
    toolCall = message.toolCalls.find(
      (tc) => tc.name === eventToolName && !tc.result,
    );
    if (toolCall) {
      console.log(`[TOOL-RESULT-DEBUG][${ts}][merge-message.ts:merge] ⚡ FALLBACK MATCHED by name! tool="${toolCall.name}"`);
    }
  }

  if (toolCall) {
    toolCall.result = event.data.content ?? "";
    console.log(`[TOOL-RESULT-DEBUG][${ts}][merge-message.ts:merge] ✅ MATCHED! Set result (len=${toolCall.result.length}) for tool "${toolCall.name}"`);
  } else {
    console.warn(`[TOOL-RESULT-DEBUG][${ts}][merge-message.ts:merge] ❌ NO MATCH! tool_call_id="${eventToolCallId}" name="${eventToolName}" not found in message.toolCalls IDs:`, existingToolCallIds, "names:", existingToolCallNames);
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
