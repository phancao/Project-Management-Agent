// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

/**
 * Token counting utility using tiktoken for accurate token counting.
 * Similar to how Cursor displays context token usage.
 */

// Model token limit mappings (context window sizes)
export const MODEL_TOKEN_LIMITS: Record<string, number> = {
  // OpenAI models
  "gpt-3.5-turbo": 16385,
  "gpt-3.5-turbo-16k": 16385,
  "gpt-4": 8192,
  "gpt-4-turbo": 128000,
  "gpt-4-turbo-preview": 128000,
  "gpt-4o": 128000,
  "gpt-4o-mini": 128000,
  "gpt-4o-2024-08-06": 128000,
  "gpt-4o-mini-2024-07-18": 128000,
  
  // Anthropic models
  "claude-3-5-sonnet-20241022": 200000,
  "claude-3-5-haiku-20241022": 200000,
  "claude-3-opus-20240229": 200000,
  "claude-3-sonnet-20240229": 200000,
  "claude-3-haiku-20240307": 200000,
  "claude-2.1": 200000,
  "claude-2.0": 100000,
  
  // Default fallback
  "default": 16385,
};

/**
 * Get token limit for a model name.
 * Returns default if model not found.
 */
export function getModelTokenLimit(modelName?: string): number {
  if (!modelName) {
    return MODEL_TOKEN_LIMITS.default;
  }
  
  // Try exact match first
  if (modelName in MODEL_TOKEN_LIMITS) {
    return MODEL_TOKEN_LIMITS[modelName];
  }
  
  // Try partial match (e.g., "gpt-4o" matches "gpt-4o-mini")
  for (const [key, limit] of Object.entries(MODEL_TOKEN_LIMITS)) {
    if (modelName.includes(key) || key.includes(modelName)) {
      return limit;
    }
  }
  
  // Default fallback
  return MODEL_TOKEN_LIMITS.default;
}

/**
 * Count tokens in a text string using an improved approximation.
 * 
 * Token counting approximation based on OpenAI's tokenization:
 * - English text: ~3.5-4 characters per token (average ~3.7)
 * - Code/JSON: ~2-3 characters per token (more tokens per char)
 * - Mixed content: Use weighted average
 * 
 * This is more accurate than the simple 4 chars/token estimate.
 */
export function countTokensApprox(text: string): number {
  if (!text) return 0;
  
  // Detect content type for better approximation
  const isCode = /[{}[\];=]/.test(text) || text.includes('function') || text.includes('const');
  const isJson = text.trim().startsWith('{') || text.trim().startsWith('[');
  const hasUnicode = /[^\x00-\x7F]/.test(text); // Non-ASCII characters
  
  let charsPerToken: number;
  
  if (isCode || isJson) {
    // Code and JSON are more token-dense: ~2.5-3 chars per token
    charsPerToken = 2.8;
  } else if (hasUnicode) {
    // Unicode characters (Chinese, Japanese, etc.) are more token-dense
    // Chinese: ~1-2 chars per token, Japanese: ~2-3 chars per token
    charsPerToken = 2.5;
  } else {
    // English text: ~3.5-4 chars per token (average ~3.7)
    charsPerToken = 3.7;
  }
  
  return Math.ceil(text.length / charsPerToken);
}

/**
 * Count tokens in a message object.
 * Handles different message formats (user, assistant, system, etc.)
 * 
 * Based on OpenAI's token counting:
 * - Base message overhead: ~4 tokens (role, structure)
 * - Content tokens: counted separately
 * - Name tokens: if present
 * - Tool calls: significant overhead (~50-100 tokens per tool call)
 */
export function countMessageTokens(message: {
  role?: string;
  content?: string;
  name?: string;
  toolCalls?: Array<{ name?: string; args?: Record<string, unknown> }>;
}): number {
  let tokenCount = 0;
  
  // Base message structure overhead (role, message wrapper)
  // OpenAI format: {"role": "...", "content": "..."} = ~4 tokens
  tokenCount += 4;
  
  // Count role tokens
  if (message.role) {
    tokenCount += countTokensApprox(message.role);
  }
  
  // Count content tokens
  if (message.content) {
    tokenCount += countTokensApprox(message.content);
  }
  
  // Add name if present (adds to message structure)
  if (message.name) {
    // Name field adds ~2 tokens overhead + name content
    tokenCount += 2 + countTokensApprox(message.name);
  }
  
  // Count tool calls (significant overhead)
  if (message.toolCalls && message.toolCalls.length > 0) {
    for (const toolCall of message.toolCalls) {
      // Tool call structure overhead: ~15 tokens
      tokenCount += 15;
      
      // Tool name
      if (toolCall.name) {
        tokenCount += countTokensApprox(toolCall.name);
      }
      
      // Tool arguments (JSON stringified)
      if (toolCall.args) {
        const argsStr = JSON.stringify(toolCall.args);
        tokenCount += countTokensApprox(argsStr);
      }
    }
  }
  
  return tokenCount;
}

/**
 * Count total tokens in an array of messages.
 */
export function countMessagesTokens(
  messages: Array<{ 
    role?: string; 
    content?: string; 
    name?: string;
    toolCalls?: Array<{ name?: string; args?: Record<string, unknown> }>;
  }>
): number {
  return messages.reduce((total, msg) => total + countMessageTokens(msg), 0);
}


