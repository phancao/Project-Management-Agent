export function autoFixMarkdown(markdown: string): string {
  let fixed = autoCloseTrailingLink(markdown);
  fixed = wrapCSVContent(fixed);
  return fixed;
}

/**
 * Detects and wraps CSV content in code blocks for proper rendering
 * Handles patterns like "CSV Export (snippet)" followed by CSV data
 * Also handles CSV content with line breaks within fields
 */
function wrapCSVContent(markdown: string): string {
  // Pattern to match CSV Export sections
  // Matches "CSV Export" or "CSV Export (snippet)" followed by CSV-like content
  // Captures until blank line, new section header, or end
  const csvExportPattern = /(CSV\s+Export\s*(?:\([^)]+\))?\s*:?\s*\n)([\s\S]*?)(?=\n\n|\n(?=[A-Z][a-z]+\s*:)|$)/gi;

  return markdown.replace(csvExportPattern, (match: string, prefix: string, csvData: string) => {
    // Check if already wrapped in code block
    if (match.includes('```')) {
      return match;
    }

    // Clean up the CSV data and reconstruct rows broken across lines
    const lines = csvData.split('\n').map((l: string) => l.trim()).filter((l: string) => l.length > 0);
    if (lines.length < 2) {
      return match; // Not enough content
    }

    // Find header row (first line with commas)
    const headerIndex = lines.findIndex((line: string) => line.includes(','));
    if (headerIndex === -1) {
      return match; // No header found
    }

    const header = lines[headerIndex]!;
    const expectedCommas = (header.match(/,/g) || []).length;

    const reconstructed: string[] = [header];
    let currentRow = '';

    // Process data rows (after header)
    for (let i = headerIndex + 1; i < lines.length; i++) {
      const line = lines[i]!;
      const commaCount = (line.match(/,/g) || []).length;
      const nextLine = i + 1 < lines.length ? lines[i + 1] : null;

      // Check if next line looks like start of new CSV row (starts with capital letter or number)
      const nextLineIsNewRow = nextLine && (
        /^[A-Z][^,]*,\d+/.test(nextLine) ||  // Name,ID pattern
        /^\d+,/.test(nextLine) ||            // ID, pattern
        (nextLine.match(/,/g) || []).length === expectedCommas && /^[A-Z]/.test(nextLine)
      );

      // If line has expected commas but next line doesn't look like new row, it might be incomplete
      if (commaCount === expectedCommas && nextLine && !nextLineIsNewRow && !/^https?:\/\//.test(nextLine)) {
        // Check if current line ends with something that suggests continuation
        if (/[\s-]$/.test(line.trim()) || nextLine.trim().startsWith('http')) {
          if (currentRow) {
            reconstructed.push(currentRow.trim());
          }
          currentRow = line;
          continue;
        }
      }

      // If line has the expected number of commas, it's likely a complete row
      if (commaCount === expectedCommas) {
        if (currentRow) {
          // Save previous incomplete row (join with space)
          reconstructed.push(currentRow.trim());
          currentRow = '';
        }
        reconstructed.push(line);
      } else if (commaCount < expectedCommas || /^https?:\/\//.test(line.trim())) {
        // This line has fewer commas or is a URL - it's likely a continuation
        if (currentRow) {
          currentRow = currentRow.trim() + ' ' + line.trim();
        } else {
          // Start a new row (might be incomplete)
          currentRow = line;
        }
      } else {
        // More commas than expected - might be a new row or malformed
        if (currentRow) {
          reconstructed.push(currentRow.trim());
        }
        currentRow = line;
      }
    }

    // Add the last row if any
    if (currentRow) {
      reconstructed.push(currentRow.trim());
    }

    const finalCSV = reconstructed.join('\n');

    // Verify it looks like CSV
    const csvLines = finalCSV.split('\n').filter(l => l.trim().length > 0);
    if (csvLines.length < 2) {
      return match;
    }

    // Check if most lines contain commas
    const linesWithCommas = csvLines.filter(line => line.includes(',')).length;
    if (linesWithCommas < csvLines.length * 0.5) {
      return match;
    }

    // Wrap in code block
    return `${prefix}\`\`\`csv\n${finalCSV}\n\`\`\``;
  });
}

/**
 * Unescape markdown-escaped characters within math delimiters
 * tiptap-markdown escapes special characters like *, _, [, ] which corrupts math formulas
 * This function restores the original LaTeX by unescaping within $...$ and $$...$$
 */
export function unescapeLatexInMath(markdown: string): string {
  let result = markdown;

  // Process inline math: $...$
  result = result.replace(/\$([^\$]+?)\$/g, (match, mathContent) => {
    const unescaped = unescapeMarkdownSpecialChars(mathContent);
    return `$${unescaped}$`;
  });

  // Process display math: $$...$$
  result = result.replace(/\$\$([\s\S]+?)\$\$/g, (match, mathContent) => {
    const unescaped = unescapeMarkdownSpecialChars(mathContent);
    return `$$${unescaped}$$`;
  });

  return result;
}

/**
 * Reverse markdown escaping for special characters
 * Order matters: process \\ last to avoid re-escaping
 */
function unescapeMarkdownSpecialChars(text: string): string {
  return text
    .replace(/\\\*/g, '*')      // \* → *
    .replace(/\\_/g, '_')       // \_ → _
    .replace(/\\\[/g, '[')      // \[ → [
    .replace(/\\\]/g, ']')      // \] → ]
    .replace(/\\\{/g, '{')      // \{ → {
    .replace(/\\\}/g, '}')      // \} → }
    .replace(/\\\\/g, '\\');    // \\ → \
}

/**
 * Normalize math delimiters for editor consumption
 * Converts display delimiters (\[...\], \\[...\\]) to $$ format
 * Converts inline delimiters (\(...\), \\(...\\)) to $ format
 * This ensures consistent format before loading into Tiptap editor
 */
export function normalizeMathForEditor(markdown: string): string {
  let normalized = markdown;

  // Convert display math - handle double backslash first to avoid conflicts
  normalized = normalized
    .replace(/\\\\\[([^\]]*)\\\\\]/g, (_match, content) => `$$${content}$$`)  // \\[...\\] → $$...$$
    .replace(/\\\[([^\]]*)\\\]/g, (_match, content) => `$$${content}$$`);  // \[...\] → $$...$$

  // Convert inline math - handle double backslash first to avoid conflicts
  normalized = normalized
    .replace(/\\\\\(([^)]*)\\\\\)/g, (_match, content) => `$${content}$`)  // \\(...\\) → $...$
    .replace(/\\\(([^)]*)\\\)/g, (_match, content) => `$${content}$`);    // \(...\) → $...$

  // Replace double backslashes with single in math contexts
  // For inline math: $...$
  normalized = normalized.replace(
    /\$([^\$]+?)\$/g,
    (match, mathContent) => {
      return `$${mathContent.replace(/\\\\/g, '\\')}$`;
    }
  );

  // For display math: $$...$$
  normalized = normalized.replace(
    /\$\$([\s\S]+?)\$\$/g,
    (match, mathContent) => {
      return `$$${mathContent.replace(/\\\\/g, '\\')}$$`;
    }
  );

  return normalized;
}

/**
 * Normalize math delimiters for display consumption
 * Ensures all math delimiters are in $$ format for remarkMath/rehypeKatex
 * This is used by the Markdown display component
 */
export function normalizeMathForDisplay(markdown: string): string {
  let normalized = markdown;

  // Convert all LaTeX-style delimiters to $$
  // Both display and inline math use $$ for display component (remarkMath handles both)
  // Handle double backslash first to avoid conflicts
  normalized = normalized
    .replace(/\\\\\[([^\]]*)\\\\\]/g, (_match, content) => `$$${content}$$`)  // \\[...\\] → $$...$$
    .replace(/\\\[([^\]]*)\\\]/g, (_match, content) => `$$${content}$$`)      // \[...\] → $$...$$
    .replace(/\\\\\(([^)]*)\\\\\)/g, (_match, content) => `$$${content}$$`)   // \\(...\\) → $$...$$
    .replace(/\\\(([^)]*)\\\)/g, (_match, content) => `$$${content}$$`);       // \(...\) → $$...$$

  // Replace double backslashes with single in math contexts
  // For inline math: $...$
  normalized = normalized.replace(
    /\$([^\$]+?)\$/g,
    (match, mathContent) => {
      return `$${mathContent.replace(/\\\\/g, '\\')}$`;
    }
  );

  // For display math: $$...$$
  normalized = normalized.replace(
    /\$\$([\s\S]+?)\$\$/g,
    (match, mathContent) => {
      return `$$${mathContent.replace(/\\\\/g, '\\')}$$`;
    }
  );

  return normalized;
}

function autoCloseTrailingLink(markdown: string): string {
  // Fix unclosed Markdown links or images
  let fixedMarkdown: string = markdown;

  // Fix unclosed image syntax ![...](...)
  fixedMarkdown = fixedMarkdown.replace(
    /!\[([^\]]*)\]\(([^)]*)$/g,
    (match: string, altText: string, url: string): string => {
      return `![${altText}](${url})`;
    },
  );

  // Fix unclosed link syntax [...](...)
  fixedMarkdown = fixedMarkdown.replace(
    /\[([^\]]*)\]\(([^)]*)$/g,
    (match: string, linkText: string, url: string): string => {
      return `[${linkText}](${url})`;
    },
  );

  // Fix unclosed image syntax ![...]
  fixedMarkdown = fixedMarkdown.replace(
    /!\[([^\]]*)$/g,
    (match: string, altText: string): string => {
      return `![${altText}]`;
    },
  );

  // Fix unclosed link syntax [...]
  fixedMarkdown = fixedMarkdown.replace(
    /\[([^\]]*)$/g,
    (match: string, linkText: string): string => {
      return `[${linkText}]`;
    },
  );

  // Fix unclosed images or links missing ")"
  fixedMarkdown = fixedMarkdown.replace(
    /!\[([^\]]*)\]\(([^)]*)$/g,
    (match: string, altText: string, url: string): string => {
      return `![${altText}](${url})`;
    },
  );

  fixedMarkdown = fixedMarkdown.replace(
    /\[([^\]]*)\]\(([^)]*)$/g,
    (match: string, linkText: string, url: string): string => {
      return `[${linkText}](${url})`;
    },
  );

  return fixedMarkdown;
}
