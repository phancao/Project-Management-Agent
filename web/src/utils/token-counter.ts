// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

/**
 * Token counting utility using tiktoken for accurate token counting.
 * Similar to how Cursor displays context token usage.
 */

// Model token limit mappings (context window sizes)
export const MODEL_TOKEN_LIMITS: Record<string, number> = {
  // OpenAI o3 series (reasoning models) - 200K context
  "o3-mini": 200000,  // CHEAPEST: $1.10/$4.40 per million | 200K context | 100K output
  "o3": 200000,  // $2.00/$8.00 per million | 200K context | 100K output
  
  // OpenAI o1 series (reasoning models)
  "o1": 200000,  // $15.00/$60.00 per million | 200K context | 100K output
  "o1-preview": 128000,  // $15.00/$60.00 per million | 128K context | 32K output
  
  // OpenAI GPT-5 series (400K context)
  "gpt-5.1": 400000,
  "gpt-5.1-preview": 400000,
  "gpt-5-mini": 400000,
  "gpt-5-nano": 400000,
  
  // OpenAI GPT-4o series (128K context)
  "gpt-4o": 128000,
  "gpt-4o-mini": 128000,
  "gpt-4o-2024-08-06": 128000,
  "gpt-4o-mini-2024-07-18": 128000,
  
  // OpenAI GPT-4 Turbo series (128K context)
  "gpt-4-turbo": 128000,
  "gpt-4-turbo-preview": 128000,
  
  // OpenAI GPT-3.5 series (16K context)
  "gpt-3.5-turbo": 16385,
  "gpt-3.5-turbo-16k": 16385,
  
  // OpenAI GPT-4 base (8K context)
  "gpt-4": 8192,
  
  // DeepSeek models
  "deepseek-reasoner": 64000,  // Approximate - verify actual limit
  "deepseek-chat": 64000,  // Approximate - verify actual limit
  
  // Dashscope Qwen models
  "qwen3-235b-a22b-thinking-2507": 200000,  // Approximate - verify actual limit
  "qwen-plus": 32000,  // Approximate - verify actual limit
  "qwen-turbo": 8000,  // Approximate - verify actual limit
  
  // Google Gemini models
  "gemini-2.0-flash-thinking-exp": 1000000,  // 1M context
  "gemini-2.0-flash-exp": 1000000,  // 1M context
  "gemini-1.5-pro": 2000000,  // 2M context
  "gemini-1.5-flash": 1000000,  // 1M context
  
  // Anthropic Claude models (200K context)
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
    return MODEL_TOKEN_LIMITS.default ?? 16385;
  }
  
  // Try exact match first
  if (modelName in MODEL_TOKEN_LIMITS) {
    const limit = MODEL_TOKEN_LIMITS[modelName];
    return limit ?? 16385;
  }
  
  // Try partial match (e.g., "gpt-4o" matches "gpt-4o-mini")
  for (const [key, limit] of Object.entries(MODEL_TOKEN_LIMITS)) {
    if (modelName.includes(key) || key.includes(modelName)) {
      return limit ?? 16385;
    }
  }
  
  // Default fallback
  return MODEL_TOKEN_LIMITS.default ?? 16385;
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
  toolCalls?: Array<{ 
    name?: string; 
    args?: Record<string, unknown>;
    argsChunks?: string[];  // Support streaming tool call args
    result?: string;  // Tool result (sent as separate ToolMessage to LLM)
  }>;
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
      // Handle both parsed args and streaming argsChunks
      if (toolCall.args) {
        // Args are already parsed (after finish_reason)
        const argsStr = JSON.stringify(toolCall.args);
        tokenCount += countTokensApprox(argsStr);
      } else if (toolCall.argsChunks && Array.isArray(toolCall.argsChunks) && toolCall.argsChunks.length > 0) {
        // Args are still streaming (before finish_reason)
        // Join chunks and count tokens
        const argsStr = toolCall.argsChunks.join("");
        tokenCount += countTokensApprox(argsStr);
      }
      
      // Count tool result (if present) - tool results are sent as separate ToolMessage objects to LLM
      // ToolMessage format: {"role": "tool", "content": "...", "tool_call_id": "..."}
      if (toolCall.result) {
        // ToolMessage structure overhead: ~8 tokens (role + tool_call_id + structure)
        tokenCount += 8;
        // Count result content
        const resultStr = String(toolCall.result);
        tokenCount += countTokensApprox(resultStr);
        // Tool call ID overhead: ~5 tokens
        tokenCount += 5;
      }
    }
  }
  
  return tokenCount;
}

/**
 * Estimate system prompt tokens based on agent type.
 * These are approximate sizes based on actual prompt templates.
 */
function estimateSystemPromptTokens(agentType?: string): number {
  if (!agentType) return 0;
  
  // Estimated system prompt sizes (in tokens) based on actual prompt templates
  const systemPromptSizes: Record<string, number> = {
    "pm_agent": 1200,      // ~4.5K chars / 3.7 = ~1200 tokens
    "researcher": 800,     // ~3K chars / 3.7 = ~800 tokens
    "planner": 1000,       // ~3.7K chars / 3.7 = ~1000 tokens
    "reporter": 600,       // ~2.2K chars / 3.7 = ~600 tokens
    "coder": 500,          // ~1.8K chars / 3.7 = ~500 tokens
    "react_agent": 400,    // ~1.5K chars / 3.7 = ~400 tokens
    "coordinator": 700,    // ~2.6K chars / 3.7 = ~700 tokens
  };
  
  const size = systemPromptSizes[agentType];
  return size !== undefined ? size : 500; // Default estimate
}

/**
 * Estimate tool definition tokens.
 * Each tool definition includes: name, description, and input schema.
 * Average: ~150-200 tokens per tool (name: ~5, description: ~50, schema: ~100-150)
 */
function estimateToolDefinitionTokens(toolNames: string[]): number {
  if (!toolNames || toolNames.length === 0) return 0;
  
  // Average tool definition size: ~180 tokens per tool
  // Includes: function name (~5), description (~50), parameters schema (~125)
  const tokensPerTool = 180;
  
  return toolNames.length * tokensPerTool;
}

/**
 * Extract unique tool names from messages (from tool calls).
 */
function extractToolNamesFromMessages(
  messages: Array<{ 
    toolCalls?: Array<{ name?: string }>;
  }>
): string[] {
  const toolNames = new Set<string>();
  
  for (const msg of messages) {
    if (msg.toolCalls && msg.toolCalls.length > 0) {
      for (const toolCall of msg.toolCalls) {
        if (toolCall.name) {
          toolNames.add(toolCall.name);
        }
      }
    }
  }
  
  return Array.from(toolNames);
}

/**
 * Count total tokens in an array of messages.
 * Like Cursor, this counts EVERYTHING that goes into the LLM context:
 * 1. System prompts (based on agent type)
 * 2. Tool definitions (based on tools actually used)
 * 3. All messages (user, assistant, system, tool)
 * 4. Tool calls and results
 */
export function countMessagesTokens(
  messages: Array<{ 
    role?: string; 
    content?: string; 
    name?: string;
    agent?: string;
    toolCalls?: Array<{ 
      name?: string; 
      args?: Record<string, unknown>;
      argsChunks?: string[];  // Support streaming tool call args
      result?: string;  // Tool result (sent as separate ToolMessage to LLM)
    }>;
  }>
): number {
  // 1. Count tokens in all messages
  let totalTokens = messages.reduce((total, msg) => total + countMessageTokens(msg), 0);
  
  // 2. Count system prompts (one per unique agent type)
  const agentTypes = new Set<string>();
  for (const msg of messages) {
    if (msg.agent) {
      agentTypes.add(msg.agent);
    }
  }
  
  // Add system prompt tokens for each agent type used
  for (const agentType of agentTypes) {
    totalTokens += estimateSystemPromptTokens(agentType);
  }
  
  // 3. Count tool definitions (based on tools actually called)
  const toolNames = extractToolNamesFromMessages(messages);
  totalTokens += estimateToolDefinitionTokens(toolNames);
  
  return totalTokens;
}


