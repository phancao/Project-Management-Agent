// Removed best-effort-json-parser import - it throws errors via callbacks that we can't suppress
// We now use only native JSON.parse with improved extraction logic

/**
 * Extract valid JSON from content that may have extra tokens.
 * Finds the last closing brace/bracket that could be valid JSON.
 * This helps avoid calling the parser library which throws errors via callbacks.
 */
function extractValidJSON(content: string): string {
  // Trim whitespace first
  content = content.trim();
  
  let braceCount = 0;
  let bracketCount = 0;
  let inString = false;
  let escapeNext = false;
  let lastValidEnd = -1;
  let startIndex = -1;

  for (let i = 0; i < content.length; i++) {
    const char = content[i];
    
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
    
    if (inString) {
      continue;
    }
    
    if (char === "{") {
      if (braceCount === 0 && bracketCount === 0) {
        startIndex = i;
      }
      braceCount++;
    } else if (char === "}") {
      if (braceCount > 0) {
        braceCount--;
        if (braceCount === 0 && bracketCount === 0) {
          lastValidEnd = i;
        }
      }
    } else if (char === "[") {
      if (braceCount === 0 && bracketCount === 0) {
        startIndex = i;
      }
      bracketCount++;
    } else if (char === "]") {
      if (bracketCount > 0) {
        bracketCount--;
        if (braceCount === 0 && bracketCount === 0) {
          lastValidEnd = i;
        }
      }
    }
  }
  
  // If we found a valid end and start, return the extracted portion
  if (lastValidEnd > 0 && startIndex >= 0) {
    const extracted = content.substring(startIndex, lastValidEnd + 1);
    // Verify the extracted portion is actually valid JSON
    try {
      JSON.parse(extracted);
      return extracted;
    } catch {
      // Extracted portion is not valid JSON, return original
      return content;
    }
  }
  
  return content;
}

/**
 * Try to parse JSON with multiple strategies
 */
function tryParseJSON<T>(raw: string): T | null {
  // Strategy 1: Try native JSON.parse (fastest, strictest)
  try {
    return JSON.parse(raw) as T;
  } catch {
    // Native parser failed, continue to next strategy
  }

  // Strategy 2: Extract valid JSON first, then try native parser
  try {
    const extracted = extractValidJSON(raw);
    if (extracted !== raw) {
      return JSON.parse(extracted) as T;
    }
  } catch {
    // Still failed, continue
  }

  // Strategy 3: Try multiple extraction strategies with native JSON.parse
  // We avoid using best-effort-json-parser because it throws errors via callbacks
  // that we can't catch or suppress, causing console errors.
  // Instead, we use improved extraction logic with native JSON.parse.
  try {
    // First, try to extract valid JSON
    const extracted = extractValidJSON(raw);
    
    // If extraction succeeded (different from raw), try native JSON.parse
    if (extracted !== raw) {
      try {
        return JSON.parse(extracted) as T;
      } catch {
        // Native parser failed on extracted portion, try more aggressive extraction
      }
    }
    
    // If extraction didn't help or native parser failed, try more aggressive extraction
    // Look for JSON-like patterns and try to extract them
    const jsonPatterns = [
      // Try to find JSON object: {...}
      /\{[\s\S]*\}/,
      // Try to find JSON array: [...]
      /\[[\s\S]*\]/,
    ];
    
    for (const pattern of jsonPatterns) {
      const match = raw.match(pattern);
      if (match && match[0]) {
        try {
          return JSON.parse(match[0]) as T;
        } catch {
          // This pattern didn't work, try next
          continue;
        }
      }
    }
    
    // Last resort: Try parsing the entire raw string (might work for simple cases)
    try {
      return JSON.parse(raw) as T;
    } catch {
      // All strategies failed, return null
      return null;
    }
  } catch {
    // If all parsing strategies failed, return null
    // The error will be handled by the caller's fallback
    return null;
  }
  
  // If we get here, all strategies failed
  return null;
}

export function parseJSON<T>(json: string | null | undefined, fallback: T) {
  if (!json) {
    return fallback;
  }
  
  try {
    const raw = json
      .trim()
      .replace(/^```json\s*/, "")
      .replace(/^```js\s*/, "")
      .replace(/^```ts\s*/, "")
      .replace(/^```plaintext\s*/, "")
      .replace(/^```\s*/, "")
      .replace(/\s*```$/, "");
    
    // Try parsing with multiple strategies
    const result = tryParseJSON<T>(raw);
    if (result !== null) {
      return result;
    }
    
    // All strategies failed, return fallback
    return fallback;
  } catch {
    // Unexpected error, return fallback
    return fallback;
  }
}
