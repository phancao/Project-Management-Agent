// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

export function deepClone<T>(value: T): T {
  // DEBUG: Log deepClone for reporter messages
  if (typeof value === 'object' && value !== null && 'agent' in value && (value as any).agent === "reporter") {
    const msg = value as any;
    const contentLen = msg.content?.length ?? 0;
    const chunksLen = msg.contentChunks?.length ?? 0;
    const lastChars = msg.content?.slice(-50) ?? "";
    console.log(`[DEBUG-DEEPCLONE] 🔄 deepClone: messageId=${msg.id}, contentLen=${contentLen}, chunksLen=${chunksLen}`);
    if (contentLen > 0) {
      console.log(`[DEBUG-DEEPCLONE] 📝 Last 50 chars before clone: "${lastChars}"`);
    }
    console.trace(`[DEBUG-DEEPCLONE] Stack trace for deepClone call`);
    
    const cloned = JSON.parse(JSON.stringify(value));
    const clonedContentLen = cloned.content?.length ?? 0;
    const clonedChunksLen = cloned.contentChunks?.length ?? 0;
    const clonedLastChars = cloned.content?.slice(-50) ?? "";
    console.log(`[DEBUG-DEEPCLONE] ✅ deepClone result: messageId=${cloned.id}, contentLen=${clonedContentLen}, chunksLen=${clonedChunksLen}`);
    if (clonedContentLen > 0) {
      console.log(`[DEBUG-DEEPCLONE] 📝 Last 50 chars after clone: "${clonedLastChars}"`);
    }
    if (contentLen > 0 && clonedContentLen === 0) {
      console.error(`[DEBUG-DEEPCLONE] ❌ CONTENT LOST in deepClone! messageId=${msg.id}, before=${contentLen}, after=${clonedContentLen}`);
      console.trace("Stack trace for content loss in deepClone");
    }
    return cloned;
  }
  return JSON.parse(JSON.stringify(value));
}
