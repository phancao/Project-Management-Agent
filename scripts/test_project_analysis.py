#!/usr/bin/env python3
"""
Test script to validate comprehensive project analysis reports.

This script:
1. Calls the backend API to generate a project analysis report
2. Validates all required sections are present
3. Checks section titles are correct
4. Verifies word counts for each section
5. Validates required components (tables, percentiles, etc.)
"""

import asyncio
import json
import re
import sys
from typing import Dict, List, Tuple
from urllib.parse import urljoin

import httpx


# Configuration
BACKEND_URL = "http://localhost:8000"
TEST_PROJECT_ID = "e6890ea6-0c3c-4a83-aa05-41b223df3284:478"  # AutoFlow QA project
# Use explicit PM analysis query that will route to PM agent
TEST_QUERY = f"Comprehensive project analysis for project {TEST_PROJECT_ID}. Include all analytics: velocity, burndown, CFD, cycle time, work distribution, issue trends, and task statistics."

# Required sections with their exact titles and word count requirements
REQUIRED_SECTIONS = {
    "A. Executive Summary": {
        "alternatives": ["Executive Summary"],
        "min_words": 200,
        "max_words": 300,
        "required_components": ["health status", "key achievements", "concerns", "recommended actions"],
    },
    "B. Sprint Overview Table": {
        "alternatives": ["Sprint Overview Table", "Sprint Overview"],
        "min_words": 100,
        "max_words": 200,
        "required_components": ["all sprints", "start date", "end date", "status", "committed", "completed", "completion %"],
    },
    "C. 📉 Burndown Chart Analysis": {
        "alternatives": ["📉 Burndown Chart Analysis", "Burndown Chart Analysis"],
        "min_words": 300,
        "max_words": 400,
        "required_components": ["current progress", "pattern analysis", "scope changes", "forecast", "recommendations"],
    },
    "D. ⚡ Velocity Chart Analysis": {
        "alternatives": ["⚡ Velocity Chart Analysis", "Velocity Chart Analysis"],
        "min_words": 300,
        "max_words": 400,
        "required_components": ["current velocity", "average velocity", "completion rates by sprint", "commitment vs delivery", "capacity planning"],
    },
    "E. 📈 Cumulative Flow Diagram (CFD) Insights": {
        "alternatives": ["📈 Cumulative Flow Diagram (CFD) Insights", "Cumulative Flow Diagram (CFD) Insights", "Cumulative Flow Diagram"],
        "min_words": 200,
        "max_words": 300,
        "required_components": ["wip analysis", "bottleneck detection", "flow efficiency", "recommendations"],
    },
    "F. ⏱️ Cycle Time Analysis": {
        "alternatives": ["⏱️ Cycle Time Analysis", "Cycle Time Analysis"],
        "min_words": 200,
        "max_words": 300,
        "required_components": ["average cycle time", "50th percentile", "85th percentile", "95th percentile", "outlier analysis"],
    },
    "G. 👥 Work Distribution Analysis": {
        "alternatives": ["👥 Work Distribution Analysis", "Work Distribution Analysis"],
        "min_words": 300,
        "max_words": 400,
        "required_components": ["by assignee table", "by status table", "by priority table", "by type table"],
    },
    "H. 📊 Issue Trend Analysis": {
        "alternatives": ["📊 Issue Trend Analysis", "Issue Trend Analysis"],
        "min_words": 200,
        "max_words": 300,
        "required_components": ["created vs resolved", "net change", "daily rates", "trend interpretation", "forecast"],
    },
    "I. Task Statistics Summary": {
        "alternatives": ["Task Statistics Summary"],
        "min_words": 150,
        "max_words": 250,
        "required_components": ["total tasks summary", "by status table", "by sprint table", "by assignee table"],
    },
    "J. 🎯 Key Insights & Recommendations": {
        "alternatives": ["🎯 Key Insights & Recommendations", "Key Insights & Recommendations"],
        "min_words": 400,
        "max_words": 500,
        "required_components": ["strengths", "concerns", "risks", "action items", "next steps"],
    },
}

# Wrong section titles that should NOT be used
WRONG_TITLES = [
    "1. Project Overview",
    "2. Project Health Metrics",
    "3. Sprints",
    "4. Task Breakdown",
    "5. Velocity Chart",
    "6. Burndown Chart",
    "7. Cumulative Flow Diagram",
    "8. Cycle Time",
    "9. Work Distribution",
    "10. Issue Trend",
    "Closing Notes",
    "Conclusion",
    "Recommendations",
]


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def extract_section(text: str, section_title: str, alternatives: List[str]) -> Tuple[str, int]:
    """Extract a section from the report text."""
    # Try exact title first
    patterns = [re.escape(section_title)] + [re.escape(alt) for alt in alternatives]
    
    for pattern in patterns:
        # Match section title (with optional emoji and formatting)
        regex = rf"(?:^|\n)#+\s*{pattern}.*?\n(.*?)(?=\n#+\s*(?:[A-J]\.|{'|'.join([re.escape(t) for t in REQUIRED_SECTIONS.keys()])})|$)"
        match = re.search(regex, text, re.DOTALL | re.IGNORECASE | re.MULTILINE)
        if match:
            section_content = match.group(1).strip()
            word_count = count_words(section_content)
            return section_content, word_count
    
    return "", 0


def check_section_title(report: str, section_key: str) -> Tuple[bool, str]:
    """Check if section title is correct."""
    section_info = REQUIRED_SECTIONS[section_key]
    all_titles = [section_key] + section_info["alternatives"]
    
    # Check for correct titles
    for title in all_titles:
        pattern = rf"#+\s*{re.escape(title)}"
        if re.search(pattern, report, re.IGNORECASE):
            return True, title
    
    # Check for wrong titles
    for wrong_title in WRONG_TITLES:
        pattern = rf"#+\s*{re.escape(wrong_title)}"
        if re.search(pattern, report, re.IGNORECASE):
            return False, f"Found wrong title: '{wrong_title}'"
    
    return False, "Section title not found"


def check_required_components(section_content: str, components: List[str]) -> List[str]:
    """Check if required components are present in section."""
    missing = []
    section_lower = section_content.lower()
    
    for component in components:
        # Check if component is mentioned
        if component.lower() not in section_lower:
            missing.append(component)
    
    return missing


async def call_chat_api(query: str) -> str:
    """Call the chat API and collect the full response."""
    # Use PM chat endpoint for project analysis
    url = urljoin(BACKEND_URL, "/api/pm/chat/stream")
    
    # PM chat endpoint uses messages array format
    # Add project_id to message content like the frontend does
    enhanced_query = f"{query}\n\nproject_id: {TEST_PROJECT_ID}"
    
    payload = {
        "messages": [
            {"role": "user", "content": enhanced_query}
        ],
        "locale": "en-US",
        "thread_id": "test_project_analysis",
        "auto_accepted_plan": True,
        "enable_background_investigation": True,
        "enable_deep_thinking": False,
        "enable_clarification": False,
        "max_plan_iterations": 1,
        "max_step_num": 10,
        "max_search_results": 3,
    }
    
    print(f"Calling API: {url}")
    print(f"Query: {query}")
    print("Waiting for response...\n")
    
    full_content = ""
    report_content = ""
    current_event_type = None
    buffer = ""
    reporter_messages = []
    all_messages = []
    
    print("Collecting stream...")
    
    async with httpx.AsyncClient(timeout=600.0) as client:  # Increased timeout to 10 minutes
        async with client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            
            async for line_bytes in response.aiter_bytes():
                # Decode bytes to string
                line = line_bytes.decode('utf-8', errors='ignore')
                buffer += line
                
                # Process complete lines (ending with \n)
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()
                    
                    if not line:
                        continue
                    
                    if line.startswith("event: "):
                        current_event_type = line[7:].strip()
                    elif line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str and data_str != "null":
                            try:
                                data = json.loads(data_str)
                                
                                if current_event_type == "message_chunk":
                                    content = data.get("content", "")
                                    agent = data.get("agent") or data.get("name") or ""
                                    
                                    # Store all messages for debugging
                                    all_messages.append({
                                        "agent": agent,
                                        "content_preview": content[:100] if content else "",
                                    })
                                    
                                    full_content += content
                                    
                                    # Look for reporter message (final report)
                                    if "reporter" in agent.lower():
                                        reporter_messages.append(content)
                                        report_content += content
                                        print(f"  ✓ Received reporter content ({len(content)} chars)")
                                
                                elif current_event_type == "tool_call_result":
                                    # Tool results might contain report data
                                    tool_result = data.get("content", "")
                                    if isinstance(tool_result, str):
                                        full_content += f"\n{tool_result}\n"
                            
                            except json.JSONDecodeError:
                                # Skip malformed JSON
                                pass
    
    print(f"\nStream complete. Collected {len(full_content)} chars total.")
    print(f"Reporter messages: {len(reporter_messages)}")
    
    # If we got reporter messages, use the last one (most complete)
    if reporter_messages:
        report_content = "".join(reporter_messages)
        print(f"Using reporter content: {len(report_content)} chars")
        
        # Filter out JSON plan content if present
        # Look for markdown headers to find actual report
        if report_content.strip().startswith("{"):
            # This is likely a plan JSON, not the report
            print("Warning: Reporter content looks like JSON plan, searching for markdown report...")
            # Try to find markdown content in full_content
            markdown_match = re.search(r'#+\s+(?:Comprehensive|Executive|A\.)', full_content, re.IGNORECASE)
            if markdown_match:
                report_content = full_content[markdown_match.start():]
                print(f"Found markdown report starting at position {markdown_match.start()}")
            else:
                # Use full content and hope the report is there
                report_content = full_content
                print("Using full content as report")
    elif not report_content:
        # Try to find report in full content by looking for markdown headers
        print("No reporter messages found, searching full content for report...")
        
        # Look for markdown headers that indicate a report
        markdown_headers = re.findall(r'^#+\s+.+', full_content, re.MULTILINE)
        if markdown_headers:
            print(f"Found {len(markdown_headers)} markdown headers")
            # Try to find the start of the report
            for marker in ["Comprehensive Project Analysis", "Executive Summary", "A. Executive Summary", "# Comprehensive"]:
                idx = full_content.find(marker)
                if idx >= 0:
                    report_content = full_content[idx:]
                    print(f"Found report starting with '{marker}'")
                    break
        
        # If still no report, use full content
        if not report_content:
            report_content = full_content
            print("Using full content as report")
    
    # Debug: show what agents we saw
    if all_messages:
        agents_seen = set(msg["agent"] for msg in all_messages if msg["agent"])
        print(f"\nAgents seen in stream: {', '.join(agents_seen) if agents_seen else 'none'}")
    
    return report_content


def validate_report(report: str) -> Dict:
    """Validate the report against all requirements."""
    results = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "sections": {},
    }
    
    print("=" * 80)
    print("VALIDATING REPORT")
    print("=" * 80)
    print()
    
    # Check each required section
    for section_key, section_info in REQUIRED_SECTIONS.items():
        print(f"Checking {section_key}...")
        
        # Check section title
        title_ok, title_msg = check_section_title(report, section_key)
        if not title_ok:
            results["valid"] = False
            results["errors"].append(f"{section_key}: {title_msg}")
            print(f"  ❌ Title check failed: {title_msg}")
            continue
        else:
            print(f"  ✅ Title: {title_msg}")
        
        # Extract section content
        section_content, word_count = extract_section(report, section_key, section_info["alternatives"])
        
        if not section_content:
            results["valid"] = False
            results["errors"].append(f"{section_key}: Section content not found")
            print(f"  ❌ Content not found")
            continue
        
        # Check word count
        min_words = section_info["min_words"]
        max_words = section_info["max_words"]
        
        if word_count < min_words:
            results["valid"] = False
            results["errors"].append(
                f"{section_key}: Word count {word_count} is below minimum {min_words}"
            )
            print(f"  ❌ Word count: {word_count} (minimum: {min_words})")
        elif word_count > max_words:
            results["warnings"].append(
                f"{section_key}: Word count {word_count} exceeds maximum {max_words}"
            )
            print(f"  ⚠️  Word count: {word_count} (maximum: {max_words})")
        else:
            print(f"  ✅ Word count: {word_count} (range: {min_words}-{max_words})")
        
        # Check required components
        missing_components = check_required_components(
            section_content, section_info["required_components"]
        )
        if missing_components:
            results["warnings"].append(
                f"{section_key}: Missing components: {', '.join(missing_components)}"
            )
            print(f"  ⚠️  Missing components: {', '.join(missing_components)}")
        else:
            print(f"  ✅ All required components present")
        
        results["sections"][section_key] = {
            "title_found": title_ok,
            "word_count": word_count,
            "missing_components": missing_components,
        }
        
        print()
    
    # Check for wrong titles
    print("Checking for wrong section titles...")
    found_wrong = []
    for wrong_title in WRONG_TITLES:
        if wrong_title.lower() in report.lower():
            found_wrong.append(wrong_title)
    
    if found_wrong:
        results["valid"] = False
        results["errors"].append(f"Found wrong section titles: {', '.join(found_wrong)}")
        print(f"  ❌ Found wrong titles: {', '.join(found_wrong)}")
    else:
        print(f"  ✅ No wrong titles found")
    
    print()
    
    return results


def print_summary(results: Dict):
    """Print validation summary."""
    print("=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print()
    
    if results["valid"]:
        print("✅ REPORT IS VALID")
    else:
        print("❌ REPORT IS INVALID")
    
    print()
    
    if results["errors"]:
        print("ERRORS:")
        for error in results["errors"]:
            print(f"  ❌ {error}")
        print()
    
    if results["warnings"]:
        print("WARNINGS:")
        for warning in results["warnings"]:
            print(f"  ⚠️  {warning}")
        print()
    
    print("SECTION DETAILS:")
    for section_key, section_data in results["sections"].items():
        status = "✅" if section_data["title_found"] and not section_data["missing_components"] else "⚠️"
        print(f"  {status} {section_key}: {section_data['word_count']} words")
    
    print()


async def main():
    """Main function."""
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = TEST_QUERY
    
    print("=" * 80)
    print("PROJECT ANALYSIS REPORT TEST")
    print("=" * 80)
    print()
    
    try:
        # Call API
        report = await call_chat_api(query)
        
        if not report:
            print("❌ ERROR: No report content received from API")
            sys.exit(1)
        
        # Save report to file
        with open("test_report_output.md", "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Report saved to test_report_output.md\n")
        
        # Validate report
        results = validate_report(report)
        
        # Print summary
        print_summary(results)
        
        # Exit with error code if invalid
        if not results["valid"]:
            sys.exit(1)
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

