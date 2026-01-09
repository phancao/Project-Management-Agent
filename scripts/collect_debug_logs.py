#!/usr/bin/env python3
"""
Debug Log Collector and Merger

Collects logs from Docker containers and merges with browser console logs.
Output: merged_debug_logs.md

Usage:
    # Collect Docker logs only (last 5 minutes)
    python scripts/collect_debug_logs.py
    
    # Collect with custom time range
    python scripts/collect_debug_logs.py --since 10m
    
    # Merge with browser logs from file
    python scripts/collect_debug_logs.py --browser-logs /path/to/browser.txt
    
    # Merge with browser logs from clipboard (paste when prompted)
    python scripts/collect_debug_logs.py --browser-clipboard
"""

import subprocess
import re
import sys
from datetime import datetime
from pathlib import Path

# Output file
OUTPUT_DIR = Path(__file__).parent.parent / ".gemini" / "brain"
OUTPUT_FILE = "merged_debug_logs.md"

# Docker containers to collect from
CONTAINERS = [
    ("pm-backend-api", "BACKEND"),
    ("pm-mcp-server", "MCP"),
]

# Log patterns to extract (less strict to capture more)
BACKEND_PATTERNS = r"(PM-AGENT|PM-TOOLS|PM-HANDLER|TOOL|DEBUG|TRACE|ERROR|DECISION|REPORTER|HANDLER|PROGRESSIVE|COUNTER|PARALLEL|DUPLICATE|ADAPTIVE|OPTIMIZER|PROMPT)"
MCP_PATTERNS = r"."  # Capture all MCP logs


def parse_docker_timestamp(line: str) -> tuple[str, str]:
    """Extract timestamp and message from Docker log line."""
    # Docker format: [HH:MM:SS.mmm] message or YYYY-MM-DD HH:MM:SS,mmm - message
    
    # Pattern 1: [10:07:16.269] message
    match = re.match(r'\[(\d{2}:\d{2}:\d{2}\.\d{3})\]\s*(.*)', line)
    if match:
        return match.group(1), match.group(2)
    
    # Pattern 2: 2026-01-08 10:07:16,269 - message
    match = re.match(r'\d{4}-\d{2}-\d{2}\s+(\d{2}:\d{2}:\d{2}),(\d{3})\s*-?\s*(.*)', line)
    if match:
        return f"{match.group(1)}.{match.group(2)}", match.group(3)
    
    # Pattern 3: INFO: timestamp - message (uvicorn)
    match = re.match(r'INFO:\s+.*"(\w+)\s+', line)
    if match:
        return "", line
    
    return "", line


def parse_browser_timestamp(line: str) -> tuple[str, str]:
    """Extract timestamp from browser console log line."""
    # Pattern: [PM-DEBUG][SSE] 2026-01-08T10:10:59.245Z message
    match = re.match(r'\[PM-DEBUG\]\[(\w+)\]\s+(\d{4}-\d{2}-\d{2}T(\d{2}:\d{2}:\d{2}\.\d{3})Z?)\s*(.*)', line)
    if match:
        component = match.group(1)
        time = match.group(3)
        message = match.group(4)
        return time, f"[{component}] {message}"
    
    return "", line


def collect_docker_logs(container: str, source: str, since: str = "5m", skip_filter: bool = False) -> list[dict]:
    """Collect logs from a Docker container."""
    logs = []
    
    try:
        # Get container logs
        cmd = ["docker", "logs", container, "--since", since]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        output = result.stdout + result.stderr
        
        for line in output.strip().split('\n'):
            if not line.strip():
                continue
            
            # Filter by patterns for backend
            if source == "BACKEND" and not re.search(BACKEND_PATTERNS, line):
                continue
            
            timestamp, message = parse_docker_timestamp(line)
            
            logs.append({
                "timestamp": timestamp,
                "source": source,
                "message": message.strip(),
                "raw": line
            })
    
    except subprocess.TimeoutExpired:
        print(f"Timeout collecting logs from {container}")
    except Exception as e:
        print(f"Error collecting logs from {container}: {e}")
    
    return logs


def collect_browser_logs(text: str) -> list[dict]:
    """Parse browser console logs."""
    logs = []
    
    for line in text.strip().split('\n'):
        if not line.strip():
            continue
        
        if "[PM-DEBUG]" not in line:
            continue
        
        timestamp, message = parse_browser_timestamp(line)
        
        logs.append({
            "timestamp": timestamp,
            "source": "FRONTEND",
            "message": message.strip(),
            "raw": line
        })
    
    return logs


def merge_logs(all_logs: list[dict]) -> list[dict]:
    """Merge and sort logs by timestamp."""
    # Sort by timestamp
    def sort_key(log):
        ts = log.get("timestamp", "")
        if not ts:
            return "99:99:99.999"
        return ts
    
    return sorted(all_logs, key=sort_key)


def format_merged_logs(logs: list[dict], test_query: str = "") -> str:
    """Format merged logs as markdown."""
    now = datetime.now().strftime("%Y-%m-%dT%H:%M")
    
    output = f"# Merged Debug Logs - {now}\n\n"
    
    if test_query:
        output += f"## Test Query: \"{test_query}\"\n\n"
    
    output += "---\n\n"
    output += "## Full Timeline (All Sources Merged by Timestamp)\n\n"
    output += "```\n"
    
    for log in logs:
        ts = log.get("timestamp", "??:??:??.???")
        source = log.get("source", "???")
        message = log.get("message", log.get("raw", ""))
        
        # Truncate very long messages
        if len(message) > 200:
            message = message[:200] + "..."
        
        output += f"{ts} [{source}] {message}\n"
    
    output += "```\n"
    
    return output


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Collect and merge debug logs")
    parser.add_argument("--since", default="5m", help="Docker logs time range (default: 5m)")
    parser.add_argument("--browser-logs", help="Path to browser console logs file")
    parser.add_argument("--browser-clipboard", action="store_true", help="Read browser logs from clipboard/stdin")
    parser.add_argument("--query", default="", help="Test query for documentation")
    parser.add_argument("--output", help="Output file path")
    
    args = parser.parse_args()
    
    all_logs = []
    
    # Collect Docker logs
    print("Collecting Docker logs...")
    for container, source in CONTAINERS:
        logs = collect_docker_logs(container, source, args.since)
        print(f"  {container}: {len(logs)} entries")
        all_logs.extend(logs)
    
    # Collect browser logs if provided
    if args.browser_logs:
        print(f"Reading browser logs from {args.browser_logs}...")
        with open(args.browser_logs, 'r') as f:
            browser_text = f.read()
        browser_logs = collect_browser_logs(browser_text)
        print(f"  Browser: {len(browser_logs)} entries")
        all_logs.extend(browser_logs)
    
    elif args.browser_clipboard:
        print("Paste browser console logs (Ctrl+D when done):")
        browser_text = sys.stdin.read()
        browser_logs = collect_browser_logs(browser_text)
        print(f"  Browser: {len(browser_logs)} entries")
        all_logs.extend(browser_logs)
    
    # Merge and sort
    print("Merging logs...")
    merged = merge_logs(all_logs)
    print(f"Total: {len(merged)} entries")
    
    # Format output
    output = format_merged_logs(merged, args.query)
    
    # Write to file
    if args.output:
        output_path = Path(args.output)
    else:
        # Find the brain directory
        output_path = Path.cwd() / "merged_debug_logs.md"
    
    output_path.write_text(output)
    print(f"\nWritten to: {output_path}")


if __name__ == "__main__":
    main()
