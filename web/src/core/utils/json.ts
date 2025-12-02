import { parse } from "best-effort-json-parser";

/**
 * Extract valid JSON from content that may have extra tokens.
 * Finds the last closing brace/bracket that could be valid JSON.
 */
function extractValidJSON(content: string): string {
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
    return content.substring(startIndex, lastValidEnd + 1);
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

  // Strategy 3: Use best-effort-json-parser (handles malformed JSON)
  // This parser can throw errors even when it successfully parses JSON
  // if there are extra tokens after the JSON. We need to handle this gracefully.
  try {
    // First, try to extract valid JSON to minimize extra tokens
    const extracted = extractValidJSON(raw);
    
    // Try parsing with best-effort-json-parser
    // Wrap in try-catch to handle "extra tokens" errors
    try {
      return parse(extracted) as T;
    } catch (parseError: unknown) {
      const parseErrorMessage = parseError instanceof Error 
        ? parseError.message 
        : String(parseError);
      
      // If the error is about "extra tokens", the parser might have
      // successfully parsed the JSON but is complaining about trailing content.
      // Try using native JSON.parse on the extracted portion.
      if (parseErrorMessage.includes("parsed json with extra tokens") || 
          parseErrorMessage.includes("extra tokens")) {
        try {
          // The JSON was likely parsed successfully, but there's extra content.
          // Try native parser on the extracted JSON.
          return JSON.parse(extracted) as T;
        } catch {
          // Native parser also failed, continue to next strategy
        }
      }
      
      // Re-throw to be caught by outer catch
      throw parseError;
    }
  } catch (error: unknown) {
    // If all parsing strategies failed, return null
    // The error will be handled by the caller's fallback
    return null;
  }
}

export function parseJSON<T>(json: string | null | undefined, fallback: T) {
  if (!json) {
    return fallback;
  }
  
  try {
    let raw = json
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
