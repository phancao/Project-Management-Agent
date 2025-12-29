// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { env } from "~/env";

import type { MCPServerMetadata } from "../mcp";
import type { Message, Resource } from "../messages";
import { extractReplayIdFromSearchParams } from "../replay/get-replay-id";
import { fetchStream } from "../sse";
import { sleep } from "../utils";

import { resolveServiceURL } from "./resolve-service-url";
import type { ChatEvent } from "./types";

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

  // Get recent messages (skip the current message which will be sent separately)
  const recentIds = messageIds.slice(-maxMessages - 1, -1);

  for (const id of recentIds) {
    const msg = messages.get(id);
    if (!msg) continue;

    // Only include user and assistant messages with content
    if (msg.role === "user" && msg.content) {
      history.push({ role: "user", content: msg.content });
    } else if (msg.role === "assistant" && msg.content) {
      // For assistant messages, use the agent type if available
      const role = msg.agent === "reporter" ? "assistant" : "assistant";
      history.push({ role, content: msg.content });
    }
  }

  return history;
}

function getLocaleFromCookie(): string {
  if (typeof document === "undefined") return "en-US";

  // Map frontend locale codes to backend locale format
  // Frontend uses: "en", "zh"
  // Backend expects: "en-US", "zh-CN"
  const LOCALE_MAP = { "en": "en-US", "zh": "zh-CN" } as const;

  // Initialize to raw locale format (matches cookie format)
  let rawLocale = "en";

  // Read from cookie
  const cookies = document.cookie.split(";");
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split("=");
    if (name === "NEXT_LOCALE" && value) {
      rawLocale = decodeURIComponent(value);
      break;
    }
  }

  // Map raw locale to backend format, fallback to en-US if unmapped
  return LOCALE_MAP[rawLocale as keyof typeof LOCALE_MAP] ?? "en-US";
}

export async function* chatStream(
  userMessage: string,
  params: {
    thread_id: string;
    resources?: Array<Resource>;
    auto_accepted_plan: boolean;
    enable_clarification?: boolean;
    max_clarification_rounds?: number;
    max_plan_iterations: number;
    max_step_num: number;
    max_search_results?: number;
    interrupt_feedback?: string;
    enable_deep_thinking?: boolean;
    enable_background_investigation: boolean;
    report_style?: "generic" | "project_management";
    mcp_settings?: {
      servers: Record<
        string,
        MCPServerMetadata & {
          enabled_tools: string[];
          add_to_agents: string[];
        }
      >;
    };
    // Conversation history for context
    conversation_history?: Array<{ role: string; content: string }>;
    // Model selection
    model_provider?: string;
    model_name?: string;
    // Search provider selection
    search_provider?: string;
  },
  options: { abortSignal?: AbortSignal } = {},
) {
  if (
    env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY ||
    (typeof window !== "undefined" && window.location.search.includes("mock")) ||
    (typeof window !== "undefined" && window.location.search.includes("replay="))
  )
    return yield* chatReplayStream(userMessage, params, options);

  try {
    const locale = getLocaleFromCookie();

    // Determine which endpoint to use based on current path
    const isPMChat = typeof window !== "undefined" && window.location.pathname.startsWith("/pm/chat");

    // Extract project context from URL if present (sent as separate field, NOT injected into message)
    const urlParams = typeof window !== "undefined" ? new URLSearchParams(window.location.search) : new URLSearchParams();
    const projectId = urlParams.get('project');

    // Use PM chat endpoint for project management tasks, DeerFlow endpoint for research
    const endpoint = isPMChat ? "pm/chat/stream" : "chat/stream";

    // Build messages array with conversation history
    const messages: Array<{ role: string; content: string }> = [];

    // Add conversation history if provided (for context continuity)
    if (params.conversation_history && params.conversation_history.length > 0) {
      messages.push(...params.conversation_history);
    }

    // Add current user message (clean, without injected context)
    messages.push({ role: "user", content: userMessage });

    const stream = fetchStream(resolveServiceURL(endpoint), {
      body: JSON.stringify({
        messages,
        locale,
        // Send project_id as separate field (not injected into message)
        // The backend will make this available via get_current_project tool
        project_id: projectId || undefined,
        ...params,
      }),
      signal: options.abortSignal,
    });

    for await (const event of stream) {
      try {
        // DEBUG: Log ALL raw SSE events to trace thoughts events
        console.log(`[chatStream] 📡 Raw SSE: event="${event.event}", hasData=${!!event.data}, dataLen=${event.data?.length ?? 0}`);
        if (event.event === "thoughts") {
          console.log(`[chatStream] 🎉 THOUGHTS SSE EVENT RECEIVED! data=${event.data}`);
        }
        // [TOOL-RESULT-DEBUG] Step 8: Log when tool_call_result SSE is received
        if (event.event === "tool_call_result") {
          const ts = new Date().toISOString().slice(11, 23);
          console.log(`[TOOL-RESULT-DEBUG][${ts}][chat.ts:SSE-received] tool_call_result event received! data=${event.data?.substring(0, 200)}...`);
        }

        // Skip events with null or empty data
        if (!event.data || event.data === 'null') {
          console.log(`[chatStream] ⏭️ Skipping empty event: type="${event.event}"`);
          continue;
        }

        const parsedData = JSON.parse(event.data);
        console.log(`[chatStream] ✅ Yielding event: type="${event.event}", id=${parsedData.id}`);
        yield {
          type: event.event,
          data: parsedData,
        } as ChatEvent;
      } catch (e) {
        // Log parse errors to help debug
        console.error(`[chatStream] ❌ Parse error for event type="${event.event}":`, e, "data=", event.data?.substring(0, 200));
      }
    }
  } catch (e) {
    // Re-raise the error so it can be handled by the caller
    // fetchStream already extracts error messages from HTTP responses
    if (e instanceof Error) {
      throw e;
    }
    throw new Error(String(e) || "Unknown error occurred");
  }
}

async function* chatReplayStream(
  userMessage: string,
  params: {
    thread_id: string;
    auto_accepted_plan: boolean;
    max_plan_iterations: number;
    max_step_num: number;
    max_search_results?: number;
    interrupt_feedback?: string;
  } = {
      thread_id: "__mock__",
      auto_accepted_plan: false,
      max_plan_iterations: 3,
      max_step_num: 1,
      max_search_results: 3,
      interrupt_feedback: undefined,
    },
  options: { abortSignal?: AbortSignal } = {},
): AsyncIterable<ChatEvent> {
  const urlParams = typeof window !== "undefined" ? new URLSearchParams(window.location.search) : new URLSearchParams();
  let replayFilePath = "";
  if (urlParams.has("mock")) {
    if (urlParams.get("mock")) {
      replayFilePath = `/mock/${urlParams.get("mock")!}.txt`;
    } else {
      if (params.interrupt_feedback === "accepted") {
        replayFilePath = "/mock/final-answer.txt";
      } else if (params.interrupt_feedback === "edit_plan") {
        replayFilePath = "/mock/re-plan.txt";
      } else {
        replayFilePath = "/mock/first-plan.txt";
      }
    }
    fastForwardReplaying = true;
  } else {
    const searchString = typeof window !== "undefined" ? window.location.search : "";
    const replayId = extractReplayIdFromSearchParams(searchString);
    if (replayId) {
      replayFilePath = `/replay/${replayId}.txt`;
    } else {
      // Fallback to a default replay
      replayFilePath = `/replay/eiffel-tower-vs-tallest-building.txt`;
    }
  }
  const text = await fetchReplay(replayFilePath, {
    abortSignal: options.abortSignal,
  });
  const normalizedText = text.replace(/\r\n/g, "\n");
  const chunks = normalizedText.split("\n\n");
  for (const chunk of chunks) {
    const [eventRaw, dataRaw] = chunk.split("\n") as [string, string];
    const [, event] = eventRaw.split("event: ", 2) as [string, string];
    const [, data] = dataRaw.split("data: ", 2) as [string, string];

    try {
      const chatEvent = {
        type: event,
        data: JSON.parse(data),
      } as ChatEvent;
      if (chatEvent.type === "message_chunk") {
        if (!chatEvent.data.finish_reason) {
          await sleepInReplay(50);
        }
      } else if (chatEvent.type === "tool_call_result") {
        await sleepInReplay(500);
      }
      yield chatEvent;
      if (chatEvent.type === "tool_call_result") {
        await sleepInReplay(800);
      } else if (chatEvent.type === "message_chunk") {
        if (chatEvent.data.role === "user") {
          await sleepInReplay(500);
        }
      }
    } catch (e) {
      console.error(e);
    }
  }
}

const replayCache = new Map<string, string>();
export async function fetchReplay(
  url: string,
  options: { abortSignal?: AbortSignal } = {},
) {
  if (replayCache.has(url)) {
    return replayCache.get(url)!;
  }
  const res = await fetch(url, {
    signal: options.abortSignal,
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch replay: ${res.statusText}`);
  }
  const text = await res.text();
  replayCache.set(url, text);
  return text;
}

export async function fetchReplayTitle() {
  const res = chatReplayStream(
    "",
    {
      thread_id: "__mock__",
      auto_accepted_plan: false,
      max_plan_iterations: 3,
      max_step_num: 1,
      max_search_results: 3,
    },
    {},
  );
  for await (const event of res) {
    if (event.type === "message_chunk") {
      return event.data.content;
    }
  }
}

export async function sleepInReplay(ms: number) {
  if (fastForwardReplaying) {
    await sleep(0);
  } else {
    await sleep(ms);
  }
}

let fastForwardReplaying = false;
export function fastForwardReplay(value: boolean) {
  fastForwardReplaying = value;
}
