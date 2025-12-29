// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { env } from "~/env";

import { type StreamEvent } from "./StreamEvent";

export async function* fetchStream(
  url: string,
  init: RequestInit,
): AsyncIterable<StreamEvent> {

  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
      },
      ...init,
    });
  } catch (error) {
    // Handle network errors (connection refused, timeout, etc.)
    if (error instanceof TypeError && error.message.includes("fetch")) {
      throw new Error(`Network error: Unable to connect to the server. Please check that the backend is running at ${url}`);
    }
    throw error;
  }

  if (response.status !== 200) {
    // Try to extract error message from response body
    let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
    try {
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorData.message || errorMessage;
      } else {
        const text = await response.text();
        if (text) {
          errorMessage = text;
        }
      }
    } catch {
      // If we can't parse the error, use the default message
    }
    throw new Error(errorMessage);
  }
  // Read from response body, event by event. An event always ends with a '\n\n'.
  const reader = response.body
    ?.pipeThrough(new TextDecoderStream())
    .getReader();
  if (!reader) {
    throw new Error("Response body is not readable");
  }

  try {
    let buffer = "";
    // Use configurable buffer size from environment, default to 1MB (1048576 bytes)
    // Default to 10MB buffer size to handle large tool responses (e.g., list_tasks with many items)
    const MAX_BUFFER_SIZE = env.NEXT_PUBLIC_MAX_STREAM_BUFFER_SIZE ?? (10 * 1024 * 1024);

    while (true) {
      let readResult;
      try {
        readResult = await reader.read();
      } catch (error) {
        // Handle abort errors gracefully - they're expected when user cancels
        const isAbortError =
          (error instanceof Error && error.name === 'AbortError') ||
          (error instanceof DOMException && error.name === 'AbortError') ||
          (error instanceof Error && (
            error.message?.toLowerCase().includes('abort') ||
            error.message?.toLowerCase().includes('aborted') ||
            error.message?.toLowerCase().includes('bodystreambuffer')
          ));

        if (isAbortError) {
          // Silently exit on abort - this is expected behavior
          break;
        }
        // Re-throw non-abort errors
        throw error;
      }

      const { done, value } = readResult;
      if (done) {
        // Handle remaining buffer data
        if (buffer.trim()) {
          const event = parseEvent(buffer.trim());
          if (event) {
            yield event;
          }
        }
        break;
      }

      buffer += value;


      // Check buffer size to avoid memory overflow
      if (buffer.length > MAX_BUFFER_SIZE) {
        throw new Error(
          `Buffer overflow - received ${(buffer.length / 1024 / 1024).toFixed(2)}MB of data without proper event boundaries. ` +
          `Max buffer size is ${(MAX_BUFFER_SIZE / 1024 / 1024).toFixed(2)}MB. ` +
          `You can increase this by setting NEXT_PUBLIC_MAX_STREAM_BUFFER_SIZE environment variable.`
        );
      }

      let newlineIndex;
      while ((newlineIndex = buffer.indexOf("\n\n")) !== -1) {
        const chunk = buffer.slice(0, newlineIndex);
        buffer = buffer.slice(newlineIndex + 2);

        if (chunk.trim()) {
          const event = parseEvent(chunk);
          if (event) {
            yield event;
          }
        }
      }
    }
  } catch (error) {
    // Handle abort errors gracefully - they're expected when user cancels
    const isAbortError =
      (error instanceof Error && error.name === 'AbortError') ||
      (error instanceof DOMException && error.name === 'AbortError') ||
      (error instanceof Error && (
        error.message?.toLowerCase().includes('abort') ||
        error.message?.toLowerCase().includes('aborted') ||
        error.message?.toLowerCase().includes('bodystreambuffer')
      ));

    if (!isAbortError) {
      // Re-throw non-abort errors
      throw error;
    }
    // Silently exit on abort - this is expected behavior
  } finally {
    reader.releaseLock(); // Release the reader lock
  }

}

function parseEvent(chunk: string) {
  let resultEvent = "message";
  let resultData: string | null = null;
  for (const line of chunk.split("\n")) {
    const pos = line.indexOf(": ");
    if (pos === -1) {
      continue;
    }
    const key = line.slice(0, pos);
    const value = line.slice(pos + 2);
    if (key === "event") {
      resultEvent = value;
    } else if (key === "data") {
      resultData = value;
    }
  }
  if (resultEvent === "message" && resultData === null) {
    return undefined;
  }
  return {
    event: resultEvent,
    data: resultData,
  } as StreamEvent;
}
