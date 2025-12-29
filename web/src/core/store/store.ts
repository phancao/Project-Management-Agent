// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { nanoid } from "nanoid";
import { toast } from "sonner";
import { create } from "zustand";
import { useShallow } from "zustand/react/shallow";

import { chatStream, generatePodcast } from "../api";
import type { Message, Resource } from "../messages";
import { mergeMessage } from "../messages";
import { parseJSON } from "../utils";

import { getChatStreamSettings } from "./settings-store";
import {
  type ResearchBlockType,
  getBlockTypeForAgent,
} from "./research-store";

/**
 * Build conversation history from messages for context.
 * This extracts user and assistant messages in chronological order.
 */
function buildConversationHistory(
  messages: Map<string, Message>,
  messageIds: string[],
  maxMessages = 20
): Array<{ role: string; content: string }> {
  const history: Array<{ role: string; content: string }> = [];

  // Get recent messages (excluding the very last one which is the current user message)
  const recentIds = messageIds.slice(Math.max(0, messageIds.length - maxMessages - 1), -1);

  for (const id of recentIds) {
    const msg = messages.get(id);
    if (!msg) continue;

    // Only include user and assistant messages with actual content
    if (msg.role === "user" && msg.content?.trim()) {
      history.push({ role: "user", content: msg.content });
    } else if (msg.role === "assistant" && msg.content?.trim()) {
      // Include assistant responses (reporter, coordinator, etc.)
      // Truncate very long responses to save tokens
      const content = msg.content.length > 2000
        ? msg.content.substring(0, 2000) + "... [truncated]"
        : msg.content;
      history.push({ role: "assistant", content });
    }
  }

  return history;
}

const THREAD_ID = nanoid();

export const useStore = create<{
  responding: boolean;
  threadId: string | undefined;
  messageIds: string[];
  messages: Map<string, Message>;
  researchIds: string[];
  researchPlanIds: Map<string, string>;
  researchReportIds: Map<string, string>;
  researchActivityIds: Map<string, string[]>;
  researchBlockTypes: Map<string, ResearchBlockType>; // Track block type for each research
  ongoingResearchId: string | null;
  openResearchId: string | null;
  // Phase 2: Separate tracking for ReAct vs Planner
  reactResearchIds: string[]; // Track ReAct agent research sessions
  plannerResearchIds: string[]; // Track Planner research sessions
  reactToPlannerEscalation: Map<string, string>; // Map: reactResearchId -> plannerResearchId
  // Progressive thoughts update counter - increments every time a thoughts event is processed
  // This forces useResearchThoughts hook to recompute even when messages Map reference doesn't change
  thoughtsUpdateCounter: number;

  appendMessage: (message: Message) => void;
  updateMessage: (message: Message) => void;
  updateMessages: (messages: Message[]) => void;
  openResearch: (researchId: string | null) => void;
  closeResearch: () => void;
  setOngoingResearch: (researchId: string | null) => void;
}>((set) => ({
  responding: false,
  threadId: THREAD_ID,
  messageIds: [],
  messages: new Map<string, Message>(),
  researchIds: [],
  researchPlanIds: new Map<string, string>(),
  researchReportIds: new Map<string, string>(),
  researchActivityIds: new Map<string, string[]>(),
  researchBlockTypes: new Map<string, ResearchBlockType>(),
  ongoingResearchId: null,
  openResearchId: null,
  // Phase 2: Separate tracking for ReAct vs Planner
  reactResearchIds: [],
  plannerResearchIds: [],
  reactToPlannerEscalation: new Map<string, string>(),
  // Progressive thoughts update counter - starts at 0
  thoughtsUpdateCounter: 0,


  appendMessage(message: Message) {
    set((state) => {
      // Prevent duplicate message IDs
      const isDuplicate = state.messageIds.includes(message.id);
      const newMessageIds = isDuplicate
        ? state.messageIds
        : [...state.messageIds, message.id];
      return {
        messageIds: newMessageIds,
        messages: new Map(state.messages).set(message.id, message),
      };
    });
  },
  updateMessage(message: Message) {
    // DEBUG: Log function entry for reporter messages


    set((state) => {
      const existing = state.messages.get(message.id);
      const existingContentLen = existing?.content?.length ?? 0;
      const newContentLen = message.content?.length ?? 0;
      const existingChunksLen = existing?.contentChunks?.length ?? 0;
      const newChunksLen = message.contentChunks?.length ?? 0;



      if (existingContentLen > 0 && newContentLen === 0 && message.agent === "reporter" && existing) {
        // Preserve existing content if new message has empty content
        message.content = existing.content;
        message.contentChunks = existing.contentChunks ?? [];
      }

      const updatedMessage = { ...message };
      const result = {
        messages: new Map(state.messages).set(message.id, updatedMessage),
      };



      return result;
    });
  },
  updateMessages(messages: Message[]) {
    set((state) => {
      const newMessages = new Map(state.messages);

      messages.forEach((m) => {
        // Functional logic: Preserve content for reporter if it disappears
        if (m.agent === "reporter") {
          const existing = state.messages.get(m.id);
          const existingContentLen = existing?.content?.length ?? 0;
          const newContentLen = m.content?.length ?? 0;

          if (existingContentLen > 0 && newContentLen === 0 && existing) {
            m.content = existing.content;
            m.contentChunks = existing.contentChunks ?? [];
          }
        }
        newMessages.set(m.id, m);
      });

      return { messages: newMessages };
    });
  },
  openResearch(researchId: string | null) {
    set({ openResearchId: researchId });
  },
  closeResearch() {
    set({ openResearchId: null });
  },
  setOngoingResearch(researchId: string | null) {
    set({ ongoingResearchId: researchId });
  },
}));

export async function sendMessage(
  content?: string,
  {
    interruptFeedback,
    resources,
  }: {
    interruptFeedback?: string;
    resources?: Array<Resource>;
  } = {},
  options: { abortSignal?: AbortSignal } = {},
) {
  if (content != null) {
    appendMessage({
      id: nanoid(),
      threadId: THREAD_ID,
      role: "user",
      content: content,
      contentChunks: [content],
      resources,
    });
  }

  const settings = getChatStreamSettings();

  // Build conversation history from existing messages for context continuity
  const state = useStore.getState();
  const conversationHistory = buildConversationHistory(
    state.messages,
    state.messageIds,
    20 // Max 20 previous messages for context
  );

  const stream = chatStream(
    content ?? "[REPLAY]",
    {
      thread_id: THREAD_ID,
      interrupt_feedback: interruptFeedback,
      resources,
      auto_accepted_plan: settings.autoAcceptedPlan,
      enable_clarification: settings.enableClarification ?? false,
      max_clarification_rounds: settings.maxClarificationRounds ?? 3,
      enable_deep_thinking: settings.enableDeepThinking ?? false,
      enable_background_investigation:
        settings.enableBackgroundInvestigation ?? true,
      max_plan_iterations: settings.maxPlanIterations,
      max_step_num: settings.maxStepNum,
      max_search_results: settings.maxSearchResults,
      report_style: settings.reportStyle,
      mcp_settings: settings.mcpSettings,
      conversation_history: conversationHistory,
      model_provider: settings.modelProvider,
      model_name: settings.modelName,
      search_provider: settings.searchProvider,
    },
    options,
  );

  setResponding(true);
  let messageId: string | undefined;

  // [FLOW-TRACE] Start of message send
  console.log(`[FLOW-TRACE] Frontend : Store : sendMessage : start : content="${(content || "").slice(0, 50)}..."`);

  const pendingUpdates = new Map<string, Message>();
  let updateTimer: NodeJS.Timeout | undefined;

  const scheduleUpdate = () => {
    if (updateTimer) clearTimeout(updateTimer);
    updateTimer = setTimeout(() => {
      // Batch update message status
      if (pendingUpdates.size > 0) {
        const reporterUpdates = Array.from(pendingUpdates.values()).filter(m => m.agent === "reporter");

        const messagesToUpdate = Array.from(pendingUpdates.values());
        useStore.getState().updateMessages(messagesToUpdate);

        // DEBUG: Log after updateMessages call


        pendingUpdates.clear();
      }
    }, 16); // ~60fps
  };

  try {
    for await (const event of stream) {
      const eventReceivedTimestamp = new Date().toISOString();
      const { type, data } = event;

      // [FLOW-TRACE] SSE Event received
      console.log(`[FLOW-TRACE] Frontend : Store : onMessage : type=${type} : id=${data?.id || "N/A"} : agent=${data?.agent || "N/A"}`);




      // DEBUG: Log all events to see what's being received
      // Check if this is a message_chunk event with reporter agent
      if (type === "message_chunk" && (data.agent === "reporter" || (data as { agent?: string }).agent === "reporter")) {
        const messageData = data as { content?: string; agent?: string; id: string; finish_reason?: string };

      }

      // Handle PM refresh events to update PM views
      // Type assertion needed because ChatEvent type doesn't include pm_refresh
      if ((type as string) === "pm_refresh") {
        if (typeof window !== "undefined") {
          window.dispatchEvent(new CustomEvent("pm_refresh", {
            detail: { type: "pm_refresh", data }
          }));
        }
        continue;
      }

      let message: Message | undefined;

      // DEBUG: Log tool_calls events to see if they're being received
      if (type === "tool_calls") {
        const timestamp = new Date().toISOString();

      }

      // Handle thoughts events: stream thoughts separately to Analysis Block
      if (type === "thoughts") {
        const timestamp = new Date().toISOString();
        const thoughtsData = data as { react_thoughts?: Array<{ thought: string; before_tool?: boolean; step_index: number }> };


        // Find or create message for thoughts
        messageId = data.id;
        if (!existsMessage(messageId)) {
          message = {
            id: messageId,
            threadId: data.thread_id,
            agent: data.agent,
            role: data.role,
            content: "",
            contentChunks: [],
            reasoningContent: "",
            reasoningContentChunks: [],
            isStreaming: true,
            interruptFeedback,
          };

          appendMessage(message);
        } else {
          message = getMessage(messageId);
        }

        if (message && thoughtsData.react_thoughts) {
          // Merge thoughts into message
          message = mergeMessage(message, event);

          updateMessage(message);

          // FIX: Add thoughts message to researchActivityIds so useResearchThoughts hook can find it
          const ongoingResearchId = useStore.getState().ongoingResearchId;
          if (ongoingResearchId) {
            const researchActivityIds = useStore.getState().researchActivityIds;
            const current = researchActivityIds.get(ongoingResearchId) ?? [];
            if (!current.includes(message.id)) {
              useStore.setState({
                researchActivityIds: new Map(researchActivityIds).set(ongoingResearchId, [...current, message.id]),
              });

            }
          }

          // FIX: Increment thoughtsUpdateCounter to force useResearchThoughts hook to recompute
          // This enables PROGRESSIVE display of thoughts as they stream in
          const currentCount = useStore.getState().thoughtsUpdateCounter;
          useStore.setState({ thoughtsUpdateCounter: currentCount + 1 });

        }
        continue; // Skip the rest of the loop for thoughts events
      }

      // Handle tool_call_result specially: use the message that contains the tool call
      if (type === "tool_call_result") {
        const toolName = data.agent || (data as any).name;
        message = findMessageByToolCallId(data.tool_call_id, toolName);
        if (message) {
          messageId = message.id;
        } else {
          continue; // Skip this event
        }
      } else {
        // For other event types, use data.id
        messageId = data.id;

        // Generate ID if missing (backend should provide it, but handle gracefully)
        if (!messageId) {
          messageId = `run--${nanoid(32)}`;
        }

        if (!existsMessage(messageId)) {
          const createTimestamp = new Date().toISOString();
          message = {
            id: messageId,
            threadId: data.thread_id,
            agent: data.agent,
            role: data.role,
            content: "",
            contentChunks: [],
            reasoningContent: "",
            reasoningContentChunks: [],
            isStreaming: true,
            interruptFeedback,
          };
          // DEBUG: Log when message is created

          // DEBUG: Log when reporter message is created
          if (data.agent === "reporter") {

          }
          appendMessage(message);
        }
      }

      message ??= getMessage(messageId);
      if (message) {
        const previousIsStreaming = message.isStreaming;
        const contentBeforeMerge = message.content?.length ?? 0;
        const chunksBeforeMerge = message.contentChunks?.length ?? 0;
        const lastCharsBefore = message.content?.slice(-50) ?? "";

        // DEBUG: Log when reporter content starts streaming
        if (message.agent === "reporter" && type === "message_chunk" && data.content) {

        }

        const mergeTimestamp = new Date().toISOString();

        message = mergeMessage(message, event);
        const contentAfterMerge = message.content?.length ?? 0;
        const chunksAfterMerge = message.contentChunks?.length ?? 0;
        const lastCharsAfter = message.content?.slice(-50) ?? "";



        // If finish_reason is present, apply update immediately to ensure UI updates quickly
        // This is especially important for reporter messages to show the final report
        if (event.data.finish_reason && previousIsStreaming) {
          // Immediately update using helper function to trigger UI re-render and run reporter logic
          if (message.agent === "reporter") {
            const finalContent = message.content ?? "";
            const finalChunks = message.contentChunks?.length ?? 0;

          }
          updateMessage(message);
          // Remove from pending updates to avoid duplicate update
          pendingUpdates.delete(message.id);
        } else {
          // Collect pending messages for update, instead of updating immediately.
          if (message.agent === "reporter") {

          }
          pendingUpdates.set(message.id, message);
          scheduleUpdate();
        }
      }
    }

    // Stream completed successfully - ensure all messages are marked as not streaming
    // Process any remaining pending updates
    if (updateTimer) clearTimeout(updateTimer);
    if (pendingUpdates.size > 0) {
      // Mark all pending messages as not streaming
      for (const [id, msg] of pendingUpdates.entries()) {
        if (msg.isStreaming) {
          msg.isStreaming = false;
        }
      }
      useStore.getState().updateMessages(Array.from(pendingUpdates.values()));
      pendingUpdates.clear();
    }

    // Ensure all messages with finish_reason are marked as not streaming
    // CRITICAL: Process reporter messages LAST so they can find the researchId from ongoingResearchId
    const state = useStore.getState();
    const finishedMessages: Message[] = [];
    const reporterMessages: Message[] = [];



    // Collect all finished messages, separating reporter messages
    // NOTE: After immediate update, isStreaming is already false, so we check finishReason only
    for (const [id, msg] of state.messages.entries()) {
      if (msg.agent === "reporter") {
        const contentLen = msg.content?.length ?? 0;

      }
      // Check if message has finishReason (regardless of isStreaming, since it might have been set to false already)
      if (msg.finishReason) {
        if (msg.isStreaming) {
          msg.isStreaming = false;
        }
        if (msg.agent === "reporter") {
          const contentLen = msg.content?.length ?? 0;

          reporterMessages.push(msg);
        } else {
          finishedMessages.push(msg);
        }
      }
    }



    // Process non-reporter messages first
    for (const msg of finishedMessages) {
      useStore.getState().updateMessage(msg);
    }

    // Process reporter messages LAST - this ensures ongoingResearchId is still available
    // updateMessage will clear ongoingResearchId when reporter finishes
    if (reporterMessages.length > 0) {

    }
    for (const msg of reporterMessages) {
      const contentLenBefore = msg.content?.length ?? 0;
      const chunksLenBefore = msg.contentChunks?.length ?? 0;
      const lastCharsBefore = msg.content?.slice(-50) ?? "";

      useStore.getState().updateMessage(msg);
    }
  } catch (error) {
    // Extract error message
    const errorMessage = error instanceof Error ? error.message : "An error occurred while generating the response. Please try again.";

    // Check if it's a provider configuration error
    const isAIProviderError = errorMessage.toLowerCase().includes("no ai providers configured") ||
      errorMessage.toLowerCase().includes("ai provider");
    const isPMProviderError = errorMessage.toLowerCase().includes("no pm providers configured") ||
      (errorMessage.toLowerCase().includes("pm provider") &&
        !errorMessage.toLowerCase().includes("ai provider"));

    if (isAIProviderError) {
      // Don't log AI provider errors to console - we show a user-friendly toast instead
      // Show error toast with action button to open Provider Management
      toast.error("AI Provider Required", {
        description: errorMessage,
        duration: 10000,
        action: {
          label: "Configure",
          onClick: () => {
            // Trigger the Provider Management dialog and open AI Providers tab
            if (typeof window !== "undefined") {
              window.dispatchEvent(new CustomEvent("pm_show_providers", {
                detail: { tab: "ai" }
              }));
            }
          },
        },
      });
    } else if (isPMProviderError) {
      // Don't log PM provider errors to console - we show a user-friendly toast instead
      // Show error toast with action button to open Provider Management
      toast.error("PM Provider Required", {
        description: errorMessage,
        duration: 10000,
        action: {
          label: "Configure",
          onClick: () => {
            // Trigger the Provider Management dialog and open PM Providers tab
            if (typeof window !== "undefined") {
              window.dispatchEvent(new CustomEvent("pm_show_providers", {
                detail: { tab: "pm" }
              }));
            }
          },
        },
      });
    } else {
      // Log other errors to console for debugging
      console.error("[Store] Error in sendMessage:", error);
      // Show regular error toast
      toast.error(errorMessage);
    }

    // Update message status.
    // TODO: const isAborted = (error as Error).name === "AbortError";
    if (messageId != null) {
      const message = getMessage(messageId);
      if (message?.isStreaming) {
        message.isStreaming = false;
        useStore.getState().updateMessage(message);
      }
    }
    useStore.getState().setOngoingResearch(null);
  } finally {
    setResponding(false);
    // Ensure all pending updates are processed.
    if (updateTimer) clearTimeout(updateTimer);
    if (pendingUpdates.size > 0) {
      useStore.getState().updateMessages(Array.from(pendingUpdates.values()));
    }

    // CRITICAL FIX: Clear ongoingResearchId when stream ends (in finally block to ensure it always runs)
    // This handles cases where the stream completes but finishReason wasn't explicitly sent
    const finalState = useStore.getState();
    const ongoingId = finalState.ongoingResearchId;
    if (ongoingId) {
      // Check if there's a reporter message for this research that has content and is not streaming
      const reportId = finalState.researchReportIds.get(ongoingId);
      if (reportId) {
        const reportMessage = finalState.messages.get(reportId);
        // If reporter message exists and is not streaming (stream ended), clear ongoingResearchId
        if (reportMessage && !reportMessage.isStreaming && reportMessage.content && reportMessage.content.length > 0) {

          useStore.getState().setOngoingResearch(null);
        }
      } else {
        // No report yet, but stream ended - check if there are any activities
        const activityIds = finalState.researchActivityIds.get(ongoingId) ?? [];
        // If we have activities but no report, and stream ended, clear ongoingResearchId
        // This prevents infinite blinking when analysis completes but no report was generated
        if (activityIds.length > 0) {

          useStore.getState().setOngoingResearch(null);
        }
      }
    }
  }
}

function setResponding(value: boolean) {
  useStore.setState({ responding: value });
}

function existsMessage(id: string) {
  return useStore.getState().messageIds.includes(id);
}

function getMessage(id: string) {
  return useStore.getState().messages.get(id);
}

function findMessageByToolCallId(toolCallId: string, toolName?: string) {
  const allMessages = Array.from(useStore.getState().messages.values());

  // Primary: exact ID match
  const exactMatch = allMessages
    .reverse()
    .find((message) => {
      if (message.toolCalls) {
        return message.toolCalls.some((toolCall) => toolCall.id === toolCallId);
      }
      return false;
    });

  if (exactMatch) {
    return exactMatch;
  }

  // Fallback: if toolName provided, match by name (for inner tool calls)
  if (toolName) {
    const nameMatch = allMessages
      .reverse()
      .find((message) => {
        if (message.toolCalls) {
          return message.toolCalls.some((tc) => tc.name === toolName && !tc.result);
        }
        return false;
      });

    if (nameMatch) {
      return nameMatch;
    }
  }

  return undefined;
}

function appendMessage(message: Message) {
  // Planner creates the research block first, then agents reuse it
  if (message.agent === "planner") {
    // Prevent creating research block with undefined message.id
    if (!message.id) {
      useStore.getState().appendMessage(message);
      return;
    }

    const state = useStore.getState();

    // INTERCEPT: If this is a TOOL_RESULT thought, merge it into the previous tool call
    // This allows the "Act" bubble to show the result (Green Box) instead of a separate text bubble
    if (message.content && message.content.includes("TOOL_RESULT:")) {
      const resultMatch = message.content.match(/TOOL_RESULT:([\s\S]*)/);
      if (resultMatch) {
        const resultJson = (resultMatch[1] || "").trim();
        // Find the last message with tool calls
        const reversedIds = [...state.messageIds].reverse();
        const lastToolMsgId = reversedIds.find(id => {
          const msg = state.messages.get(id);
          return msg?.toolCalls && msg.toolCalls.length > 0;
        });

        if (lastToolMsgId) {
          const lastToolMsg = state.messages.get(lastToolMsgId);
          if (lastToolMsg && lastToolMsg.toolCalls) {
            // Update the last tool call with this result
            // VALIDATION: Only merge if it looks like JSON or if it's a Meta Tool (which returns text)
            const toolName = lastToolMsg.toolCalls[0]?.name;
            const isMetaTool = toolName === "pm_agent" || toolName === "planner";
            const isJson = resultJson.startsWith("{") || resultJson.startsWith("[");

            if (!isMetaTool && !isJson) {
              return;
            }

            const updatedToolCalls = [...lastToolMsg.toolCalls];
            const lastIdx = updatedToolCalls.length - 1;
            updatedToolCalls[lastIdx] = {
              ...updatedToolCalls[lastIdx],
              result: resultJson
            } as any;

            // Update the message in store
            useStore.setState({
              messages: new Map(state.messages).set(lastToolMsgId, {
                ...lastToolMsg,
                toolCalls: updatedToolCalls
              })
            });
            console.log(`[Store] 🔗 Merged TOOL_RESULT into message ${lastToolMsgId}`);

            // OPTIONAL: Still append the message?
            // If we swallow it, we lose the "Thought N" index if user relies on it.
            // But user wants "Standard Chat Bubble" result.
            // If we render duplication, it's confusing.
            // Let's swallowing it to keep stream clean.
            return;
          }
        }
      }
    }

    // Check if this planner message already has a block
    if (state.researchIds.includes(message.id)) {
      appendResearchActivity(message);
      useStore.getState().appendMessage(message);
      return;
    }

    // Phase 2: Track planner research ID
    if (!state.plannerResearchIds.includes(message.id)) {
      useStore.setState({
        plannerResearchIds: [...state.plannerResearchIds, message.id],
      });
    }

    // Phase 2: Check for ReAct escalation
    // If there's an ongoing ReAct research, link it to this planner research
    if (state.ongoingResearchId && state.reactResearchIds.includes(state.ongoingResearchId)) {
      const reactResearchId = state.ongoingResearchId;
      console.log(`[Store] 🔄 ReAct escalation detected: linking reactResearchId=${reactResearchId} to plannerResearchId=${message.id}`);
      useStore.setState({
        reactToPlannerEscalation: new Map(state.reactToPlannerEscalation).set(reactResearchId, message.id),
      });
    }

    // Planner creates the research block
    appendResearch(message.id, "planner");
    openResearch(message.id);
    useStore.getState().setOngoingResearch(message.id);
    appendResearchActivity(message);
    useStore.getState().appendMessage(message);
    return;
  }

  // Track research activities for execution agents (they reuse planner's block)
  if (
    message.agent === "coder" ||
    message.agent === "reporter" ||
    message.agent === "researcher" ||
    message.agent === "pm_agent"
  ) {
    const state = useStore.getState();



    const blockType = getBlockTypeForAgent(message.agent);

    // Check if this message already belongs to a research block
    let existingBlockForThisMessage: string | null = null;

    if (state.researchIds.includes(message.id)) {
      existingBlockForThisMessage = message.id;
    } else {
      for (const [researchId, activityIds] of state.researchActivityIds.entries()) {
        if (activityIds.includes(message.id)) {
          existingBlockForThisMessage = researchId;
          break;
        }
      }
    }

    // If message already belongs to a block, reuse it
    // ROOT CAUSE FIX: Don't call appendResearchActivity if message is already in activityIds
    // This prevents duplicate entries in activityIds which causes duplicate tool calls
    if (existingBlockForThisMessage) {
      if (state.ongoingResearchId !== existingBlockForThisMessage) {
        useStore.getState().setOngoingResearch(existingBlockForThisMessage);
      }
      // Message is already in activityIds, so don't add it again
      // Just update the message in the store
      useStore.getState().appendMessage(message);
      return;
    }

    // Reuse ongoing research block if it exists
    let blockToUse: string | null = null;

    if (state.ongoingResearchId) {
      blockToUse = state.ongoingResearchId;
    } else {
      // Find most recent planner block
      const reversedIds = [...state.researchIds].reverse();
      for (const researchId of reversedIds.slice(0, 5)) {
        const existingType = state.researchBlockTypes.get(researchId);
        if (existingType === "planner") {
          blockToUse = researchId;
          break;
        }
      }

      // Fallback: Find most recent block of same type
      if (!blockToUse) {
        for (const researchId of reversedIds.slice(0, 5)) {
          const existingType = state.researchBlockTypes.get(researchId);
          if (existingType === blockType) {
            blockToUse = researchId;
            break;
          }
        }
      }
    }

    if (blockToUse) {
      if (state.ongoingResearchId !== blockToUse) {
        useStore.getState().setOngoingResearch(blockToUse);
      }
      appendResearchActivity(message);
    } else {
      // Create new block only if truly no existing block
      appendResearch(message.id, blockType);
      openResearch(message.id);
      useStore.getState().setOngoingResearch(message.id);
      appendResearchActivity(message);
    }
  }
  useStore.getState().appendMessage(message);
}

function updateMessage(message: Message) {
  // INTERCEPT (Streaming): Catch late-arriving TOOL_RESULT content that wasn't caught by appendMessage
  // This handles cases where appendMessage saw empty content, but updateMessage sees the "TOOL_RESULT:..." text
  if (message.content && message.content.includes("TOOL_RESULT:")) {
    const resultMatch = message.content.match(/TOOL_RESULT:([\s\S]*)/);
    if (resultMatch) {
      const state = useStore.getState();
      const resultJson = (resultMatch[1] || "").trim();

      // Find the last message with tool calls
      const reversedIds = [...state.messageIds].reverse();
      const lastToolMsgId = reversedIds.find(id => {
        // Skip SELF (if this message is already in the list)
        if (id === message.id) return false;
        const msg = state.messages.get(id);
        return msg?.toolCalls && msg.toolCalls.length > 0;
      });

      if (lastToolMsgId) {
        const lastToolMsg = state.messages.get(lastToolMsgId);
        if (lastToolMsg && lastToolMsg.toolCalls) {
          // VALIDATION: Only merge if it looks like JSON or if it's a Meta Tool
          const toolName = lastToolMsg.toolCalls[0]?.name;
          const isMetaTool = toolName === "pm_agent" || toolName === "planner";
          const isJson = resultJson.startsWith("{") || resultJson.startsWith("[");

          if (!isMetaTool && !isJson) {
            return;
          }

          const updatedToolCalls = [...lastToolMsg.toolCalls];
          const lastIdx = updatedToolCalls.length - 1;

          // Only update if not already set (or force update)
          updatedToolCalls[lastIdx] = {
            ...updatedToolCalls[lastIdx],
            result: resultJson
          } as any;

          // Update previous message
          const newMessages = new Map(state.messages);
          newMessages.set(lastToolMsgId, {
            ...lastToolMsg,
            toolCalls: updatedToolCalls
          });

          // DELETE the current message (swallow it)
          // This removes the "Tool Result" text bubble if it started rendering
          if (newMessages.has(message.id)) {
            newMessages.delete(message.id);
            // Also remove from messageIds
            const newMessageIds = state.messageIds.filter(id => id !== message.id);
            useStore.setState({
              messages: newMessages,
              messageIds: newMessageIds
            });
            console.log(`[Store] 🔗 Streaming Merged TOOL_RESULT into message ${lastToolMsgId} and deleted ${message.id}`);
          } else {
            useStore.setState({ messages: newMessages });
          }
          return;
        }
      }
    }
  }

  // DEBUG: Log function entry for reporter messages
  if (message.agent === "reporter") {
    const contentLen = message.content?.length ?? 0;
    const chunksLen = message.contentChunks?.length ?? 0;
    const lastChars = message.content?.slice(-50) ?? "";
    console.log(`[DEBUG-HELPER-ENTRY] 🚪 updateMessage helper ENTRY: messageId=${message.id}, contentLen=${contentLen}, chunksLen=${chunksLen}, isStreaming=${message.isStreaming}, finishReason=${message.finishReason}`);
    if (contentLen > 0) {
      console.log(`[DEBUG-HELPER-ENTRY] 📝 Last 50 chars: "${lastChars}"`);
    }
    console.trace(`[DEBUG-HELPER-ENTRY] Stack trace for helper updateMessage entry`);
  }

  if (message.agent === "reporter" && !message.isStreaming) {
    const contentLen = message.content?.length ?? 0;
    const chunksLen = message.contentChunks?.length ?? 0;
    const lastChars = message.content?.slice(-50) ?? "";
    console.log(`[DEBUG-REPORTER-HELPER] 🔧 updateMessage helper: messageId=${message.id}, contentLen=${contentLen}, chunksLen=${chunksLen}, isStreaming=${message.isStreaming}, finishReason=${message.finishReason}`);
    if (contentLen > 0) {
      console.log(`[DEBUG-REPORTER-HELPER] 📝 Last 50 chars: "${lastChars}"`);
    }
    console.trace(`[DEBUG-REPORTER-HELPER] Stack trace for helper updateMessage call`);

    let researchId = getOngoingResearchId();

    // Find the research that has this reporter message
    if (!researchId) {
      const state = useStore.getState();

      for (const [rId, reportId] of state.researchReportIds.entries()) {
        if (reportId === message.id) {
          researchId = rId;
          break;
        }
      }
      if (!researchId) {
        for (const [rId, activityIds] of state.researchActivityIds.entries()) {
          if (activityIds.includes(message.id)) {
            researchId = rId;
            break;
          }
        }
      }
    }

    if (researchId) {
      const currentReportId = useStore.getState().researchReportIds.get(researchId);
      console.log(`[Store.updateMessage helper] Setting researchReportIds: researchId=${researchId}, currentReportId=${currentReportId}, newReportId=${message.id}, contentLen=${contentLen}`);

      // Only set reportId if:
      // 1. No current reportId exists (first time), OR
      // 2. New message has content (even if different from current), OR
      // 3. Same message ID (updating existing message)
      // DO NOT overwrite existing reportId with empty message
      const shouldSetReportId = !currentReportId || contentLen > 0 || currentReportId === message.id;

      if (shouldSetReportId && (!currentReportId || currentReportId !== message.id)) {
        // WARNING: If we're setting a report with empty content when there's an existing one, log it
        if (contentLen === 0 && currentReportId) {
          const currentMsg = useStore.getState().messages.get(currentReportId);
          const currentContentLen = currentMsg?.content?.length ?? 0;
          console.warn(`[Store.updateMessage helper] ⚠️ Setting empty reportId when existing one has content: researchId=${researchId}, oldReportId=${currentReportId} (contentLen=${currentContentLen}), newReportId=${message.id} (contentLen=0)`);
        }
        useStore.setState({
          researchReportIds: new Map(useStore.getState().researchReportIds).set(
            researchId,
            message.id,
          ),
        });
      } else if (!shouldSetReportId) {
        // Prevent overwriting existing reportId with empty message
        const currentMsg = useStore.getState().messages.get(currentReportId!);
        const currentContentLen = currentMsg?.content?.length ?? 0;
        console.warn(`[Store.updateMessage helper] 🛑 PREVENTED overwriting reportId with empty message: researchId=${researchId}, keeping oldReportId=${currentReportId} (contentLen=${currentContentLen}), rejecting newReportId=${message.id} (contentLen=0)`);
      }

      // Auto-open the research when report finishes
      useStore.getState().openResearch(researchId);

      // Clear ongoingResearchId when report finishes (has finishReason and not streaming)
      if (message.finishReason && !message.isStreaming) {
        const currentOngoing = useStore.getState().ongoingResearchId;
        if (currentOngoing === researchId) {
          console.log(`[Store.updateMessage helper] ✅ Clearing ongoingResearchId: researchId=${researchId}, report finished`);
          useStore.getState().setOngoingResearch(null);
        }
      }
    } else {
      // Fallback: Try to find researchId by checking activityIds
      const state = useStore.getState();
      for (const [rId, activityIds] of state.researchActivityIds.entries()) {
        if (activityIds.includes(message.id)) {
          const currentReportId = state.researchReportIds.get(rId);
          const contentLen = message.content?.length ?? 0;

          console.log(`[Store.updateMessage helper] 🔍 Fallback found researchId via activityIds: researchId=${rId}, currentReportId=${currentReportId}, newReportId=${message.id}, contentLen=${contentLen}`);

          // Only set reportId if no existing one OR new message has content
          if (!currentReportId || contentLen > 0) {
            if (contentLen === 0 && currentReportId) {
              const currentMsg = state.messages.get(currentReportId);
              const currentContentLen = currentMsg?.content?.length ?? 0;
              console.warn(`[Store.updateMessage helper] ⚠️ Fallback: Setting empty reportId when existing one has content: researchId=${rId}, oldReportId=${currentReportId} (contentLen=${currentContentLen}), newReportId=${message.id} (contentLen=0)`);
            }
            useStore.setState({
              researchReportIds: new Map(state.researchReportIds).set(rId, message.id),
            });
            useStore.getState().openResearch(rId);

            // Clear ongoingResearchId when report finishes (has finishReason and not streaming)
            if (message.finishReason && !message.isStreaming) {
              const currentOngoing = useStore.getState().ongoingResearchId;
              if (currentOngoing === rId) {
                console.log(`[Store.updateMessage helper] ✅ Clearing ongoingResearchId (fallback): researchId=${rId}, report finished`);
                useStore.getState().setOngoingResearch(null);
              }
            }
          } else {
            const currentMsg = state.messages.get(currentReportId!);
            const currentContentLen = currentMsg?.content?.length ?? 0;
            console.warn(`[Store.updateMessage helper] 🛑 PREVENTED fallback overwrite with empty message: researchId=${rId}, keeping oldReportId=${currentReportId} (contentLen=${currentContentLen}), rejecting newReportId=${message.id} (contentLen=0)`);
          }
          break;
        }
      }
    }
  }

  // DEBUG: Log before calling store's updateMessage
  if (message.agent === "reporter") {
    const contentLen = message.content?.length ?? 0;
    const chunksLen = message.contentChunks?.length ?? 0;
    const lastChars = message.content?.slice(-50) ?? "";
    console.log(`[DEBUG-HELPER-BEFORE-UPDATE] 🔧 About to call store.updateMessage: messageId=${message.id}, contentLen=${contentLen}, chunksLen=${chunksLen}`);
    if (contentLen > 0) {
      console.log(`[DEBUG-HELPER-BEFORE-UPDATE] 📝 Last 50 chars: "${lastChars}"`);
    }
  }

  useStore.getState().updateMessage(message);

  // DEBUG: Log after calling store's updateMessage
  if (message.agent === "reporter") {
    const state = useStore.getState();
    const updatedMsg = state.messages.get(message.id);
    const finalContentLen = updatedMsg?.content?.length ?? 0;
    const finalChunksLen = updatedMsg?.contentChunks?.length ?? 0;
    const finalLastChars = updatedMsg?.content?.slice(-50) ?? "";
    console.log(`[DEBUG-HELPER-AFTER-UPDATE] 🔧 After store.updateMessage: messageId=${message.id}, finalContentLen=${finalContentLen}, finalChunksLen=${finalChunksLen}`);
    if (finalContentLen > 0) {
      console.log(`[DEBUG-HELPER-AFTER-UPDATE] 📝 Final last 50 chars: "${finalLastChars}"`);
    }
    console.log(`[DEBUG-HELPER-EXIT] 🚪 updateMessage helper EXIT: messageId=${message.id}`);
  }
}

function getOngoingResearchId() {
  return useStore.getState().ongoingResearchId;
}

function appendResearch(researchId: string, blockType: ResearchBlockType) {
  // Prevent creating research block with undefined/null researchId
  if (!researchId) {
    return;
  }

  // Check if this research already exists
  const state = useStore.getState();
  if (state.researchIds.includes(researchId)) {
    return;
  }

  let planMessage: Message | undefined;
  const reversedMessageIds = [...state.messageIds].reverse();
  for (const messageId of reversedMessageIds) {
    const message = getMessage(messageId);
    if (message?.agent === "planner") {
      planMessage = message;
      break;
    }
  }

  const messageIds = [researchId];
  const newResearchIds = [...useStore.getState().researchIds, researchId];

  // Add planner message if it exists (may not exist for ReAct fast path)
  if (planMessage?.id) {
    messageIds.unshift(planMessage.id);
    useStore.setState({
      ongoingResearchId: researchId,
      researchIds: newResearchIds,
      researchPlanIds: new Map(useStore.getState().researchPlanIds).set(
        researchId,
        planMessage.id,
      ),
      researchActivityIds: new Map(useStore.getState().researchActivityIds).set(
        researchId,
        messageIds,
      ),
      researchBlockTypes: new Map(useStore.getState().researchBlockTypes).set(
        researchId,
        blockType,
      ),
    });
  } else {
    // Fast path (ReAct) - no planner message
    useStore.setState({
      ongoingResearchId: researchId,
      researchIds: newResearchIds,
      researchActivityIds: new Map(useStore.getState().researchActivityIds).set(
        researchId,
        messageIds,
      ),
      researchBlockTypes: new Map(useStore.getState().researchBlockTypes).set(
        researchId,
        blockType,
      ),
    });
  }
}

function appendResearchActivity(message: Message) {
  const researchId = getOngoingResearchId();

  if (researchId) {
    const researchActivityIds = useStore.getState().researchActivityIds;
    const current = researchActivityIds.get(researchId);

    // Initialize or add to activity ids
    if (!current) {
      useStore.setState({
        researchActivityIds: new Map(researchActivityIds).set(researchId, [message.id]),
      });
    } else if (!current.includes(message.id)) {
      useStore.setState({
        researchActivityIds: new Map(researchActivityIds).set(researchId, [
          ...current,
          message.id,
        ]),
      });
    }

    // Set reportId for reporter messages
    // CRITICAL: Only set if message has content OR no existing reportId exists
    // This prevents empty reporter messages (from tool_calls) from overwriting full reports
    if (message.agent === "reporter") {
      const state = useStore.getState();
      const currentReportId = state.researchReportIds.get(researchId);
      const contentLen = message.content?.length ?? 0;

      // Only set reportId if: no existing one OR new message has content OR same message ID
      const shouldSetReportId = !currentReportId || contentLen > 0 || currentReportId === message.id;

      if (shouldSetReportId && (!currentReportId || currentReportId !== message.id)) {
        if (contentLen === 0 && currentReportId) {
          const currentMsg = state.messages.get(currentReportId);
          const currentContentLen = currentMsg?.content?.length ?? 0;
          console.warn(`[appendResearchActivity] ⚠️ Setting empty reportId when existing one has content: researchId=${researchId}, oldReportId=${currentReportId} (contentLen=${currentContentLen}), newReportId=${message.id} (contentLen=0)`);
        }
        useStore.setState({
          researchReportIds: new Map(state.researchReportIds).set(
            researchId,
            message.id,
          ),
        });
      } else if (!shouldSetReportId) {
        const currentMsg = state.messages.get(currentReportId!);
        const currentContentLen = currentMsg?.content?.length ?? 0;
        console.warn(`[appendResearchActivity] 🛑 PREVENTED overwriting reportId with empty message: researchId=${researchId}, keeping oldReportId=${currentReportId} (contentLen=${currentContentLen}), rejecting newReportId=${message.id} (contentLen=0)`);
      }
    }
  }
}

export function openResearch(researchId: string | null) {
  useStore.getState().openResearch(researchId);
}

export function closeResearch() {
  useStore.getState().closeResearch();
}

export async function listenToPodcast(researchId: string) {
  const planMessageId = useStore.getState().researchPlanIds.get(researchId);
  const reportMessageId = useStore.getState().researchReportIds.get(researchId);
  if (planMessageId && reportMessageId) {
    const planMessage = getMessage(planMessageId)!;
    const title = parseJSON(planMessage.content, { title: "Untitled" }).title;
    const reportMessage = getMessage(reportMessageId);
    if (reportMessage?.content) {
      appendMessage({
        id: nanoid(),
        threadId: THREAD_ID,
        role: "user",
        content: "Please generate a podcast for the above research.",
        contentChunks: [],
      });
      const podCastMessageId = nanoid();
      const podcastObject = { title, researchId };
      const podcastMessage: Message = {
        id: podCastMessageId,
        threadId: THREAD_ID,
        role: "assistant",
        agent: "podcast",
        content: JSON.stringify(podcastObject),
        contentChunks: [],
        reasoningContent: "",
        reasoningContentChunks: [],
        isStreaming: true,
      };
      appendMessage(podcastMessage);
      // Generating podcast...
      let audioUrl: string | undefined;
      try {
        audioUrl = await generatePodcast(reportMessage.content);
      } catch (e) {
        console.error(e);
        useStore.setState((state) => ({
          messages: new Map(useStore.getState().messages).set(
            podCastMessageId,
            {
              ...state.messages.get(podCastMessageId)!,
              content: JSON.stringify({
                ...podcastObject,
                error: e instanceof Error ? e.message : "Unknown error",
              }),
              isStreaming: false,
            },
          ),
        }));
        toast("An error occurred while generating podcast. Please try again.");
        return;
      }
      useStore.setState((state) => ({
        messages: new Map(useStore.getState().messages).set(podCastMessageId, {
          ...state.messages.get(podCastMessageId)!,
          content: JSON.stringify({ ...podcastObject, audioUrl }),
          isStreaming: false,
        }),
      }));
    }
  }
}

export function useResearchMessage(researchId: string) {
  return useStore(
    useShallow((state) => {
      const messageId = state.researchPlanIds.get(researchId);
      return messageId ? state.messages.get(messageId) : undefined;
    }),
  );
}

export function useMessage(messageId: string | null | undefined) {
  return useStore(
    useShallow((state) =>
      messageId ? state.messages.get(messageId) : undefined,
    ),
  );
}

export function useMessageIds() {
  return useStore(useShallow((state) => state.messageIds));
}

export function useRenderableMessageIds() {
  return useStore(
    useShallow((state) => {
      // Filter to only messages that will actually render in MessageListView
      // This prevents duplicate keys and React warnings when messages change state
      const seen = new Set<string>();
      return state.messageIds.filter((messageId) => {
        // Skip null/undefined/empty messageIds
        if (!messageId) {
          return false;
        }
        // Skip duplicates to ensure unique keys
        if (seen.has(messageId)) {
          return false;
        }
        seen.add(messageId);

        const message = state.messages.get(messageId);
        if (!message) return false;

        // Only include messages that match MessageListItem rendering conditions
        // These are the same conditions checked in MessageListItem component
        // Note: reporter is NOT included - report is shown inside AnalysisBlock
        return (
          message.role === "user" ||
          message.agent === "coordinator" ||
          message.agent === "planner" ||
          message.agent === "podcast" ||
          message.agent === "pm_agent" ||
          message.agent === "react_agent" ||
          state.researchIds.includes(messageId) // startOfResearch condition
        );
      });
    }),
  );
}

export function useLastInterruptMessage() {
  return useStore(
    useShallow((state) => {
      if (state.messageIds.length >= 2) {
        const lastMessage = state.messages.get(
          state.messageIds[state.messageIds.length - 1]!,
        );
        return lastMessage?.finishReason === "interrupt" ? lastMessage : null;
      }
      return null;
    }),
  );
}

export function useLastFeedbackMessageId() {
  const waitingForFeedbackMessageId = useStore(
    useShallow((state) => {
      if (state.messageIds.length >= 2) {
        const lastMessage = state.messages.get(
          state.messageIds[state.messageIds.length - 1]!,
        );
        if (lastMessage?.finishReason === "interrupt") {
          return state.messageIds[state.messageIds.length - 2];
        }
      }
      return null;
    }),
  );
  return waitingForFeedbackMessageId;
}

export function useToolCalls() {
  return useStore(
    useShallow((state) => {
      return state.messageIds
        ?.map((id) => getMessage(id)?.toolCalls)
        .filter((toolCalls) => toolCalls != null)
        .flat();
    }),
  );
}
