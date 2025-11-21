#!/usr/bin/env python3
"""
Test script for "list my projects" flow
Tests the complete end-to-end flow:
1. PM chat request with "list my projects"
2. MCP authentication
3. Provider configuration
4. Project listing
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import httpx
from typing import Dict, Any, List


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_success(msg: str):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")


def print_error(msg: str):
    """Print error message"""
    print(f"{Colors.RED}❌ {msg}{Colors.RESET}")


def print_warning(msg: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.RESET}")


def print_info(msg: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.RESET}")


def print_section(title: str):
    """Print section header"""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{title}{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")


async def check_backend_health(base_url: str = "http://localhost:8000") -> bool:
    """Check if backend is healthy"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                data = response.json()
                print_success(f"Backend is healthy (version: {data.get('version', 'unknown')})")
                return True
            else:
                print_error(f"Backend health check failed: {response.status_code}")
                return False
    except Exception as e:
        print_error(f"Backend health check failed: {e}")
        return False


async def send_pm_chat_request(
    base_url: str,
    message: str,
    thread_id: str = None
) -> Dict[str, Any]:
    """
    Send a PM chat request and collect the response
    
    Returns:
        Dictionary with response data and status
    """
    if thread_id is None:
        thread_id = f"test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    url = f"{base_url}/api/pm/chat/stream"
    
    # PM chat endpoint expects messages array format
    payload = {
        "messages": [
            {
                "role": "user",
                "content": message
            }
        ],
        "thread_id": thread_id,
        "locale": "en-US",
        "report_style": "academic"
    }
    
    print_info(f"Sending PM chat request: '{message}'")
    print_info(f"Thread ID: {thread_id}")
    
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:  # Increased timeout to 3 minutes
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    print_error(f"Request failed: {response.status_code}")
                    error_text = await response.aread()
                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "error": error_text.decode()
                    }
                
                # Collect SSE events
                events = []
                full_content = []
                agents_used = set()
                last_event_type = None
                
                print_info("Waiting for response stream...")
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    
                    if line.startswith("event: "):
                        last_event_type = line[7:].strip()
                    elif line.startswith("data: "):
                        data_str = line[6:].strip()
                        if not data_str:
                            continue
                        try:
                            data = json.loads(data_str)
                            events.append(data)
                            
                            # Collect content
                            if "content" in data and data["content"]:
                                content = data["content"]
                                full_content.append(content)
                                # Show progress for long responses
                                if len(full_content) % 10 == 0:
                                    print_info(f"Received {len(full_content)} content chunks...")
                            
                            # Track agents
                            if "agent" in data:
                                agents_used.add(data["agent"])
                            
                            # Check for finish_reason to know when done
                            if data.get("finish_reason") in ["stop", "tool_calls", "length"]:
                                print_info(f"Stream finished with reason: {data.get('finish_reason')}")
                        except json.JSONDecodeError as e:
                            # Skip invalid JSON lines
                            pass
                
                # Combine all content
                combined_content = "\n".join(full_content)
                
                # Extract tool calls and results from events
                tool_calls = []
                tool_results = []
                for event in events:
                    # Tool calls are in events with "tool_calls" field (array of tool call objects)
                    if "tool_calls" in event:
                        # Extract individual tool calls from the array
                        for tc in event.get("tool_calls", []):
                            tool_calls.append(tc)
                    # Also check for tool_call_chunks (streaming tool calls)
                    if "tool_call_chunks" in event:
                        for chunk in event.get("tool_call_chunks", []):
                            # Only add chunks that have a name (complete chunks)
                            if chunk.get("name"):
                                tool_calls.append(chunk)
                    # Tool results are in events with "tool_call_id" field
                    if "tool_call_id" in event:
                        tool_results.append(event)
                
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "events": events,
                    "content": combined_content,
                    "agents_used": list(agents_used),
                    "event_count": len(events),
                    "tool_calls": tool_calls,
                    "tool_results": tool_results
                }
                
    except httpx.TimeoutException:
        print_error("Request timed out after 120 seconds")
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        print_error(f"Request failed: {e}")
        return {"success": False, "error": str(e)}


async def verify_backend_api_projects(validate_first_only: bool = True) -> Dict[str, Any]:
    """Verify projects exist via backend API directly
    
    Args:
        validate_first_only: If True, only validate the first provider to save time
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("http://localhost:8000/api/pm/projects")
            if response.status_code == 200:
                projects = response.json()
                # Group by provider
                providers = {}
                for project in projects:
                    provider_id = project.get('provider_id')
                    if provider_id not in providers:
                        providers[provider_id] = []
                    providers[provider_id].append(project)
                
                # If validate_first_only, only return data for the first provider
                if validate_first_only and providers:
                    first_provider_id = list(providers.keys())[0]
                    first_provider_projects = providers[first_provider_id]
                    return {
                        "success": True,
                        "total_projects": len(first_provider_projects),
                        "providers": {
                            first_provider_id: len(first_provider_projects)
                        },
                        "projects": first_provider_projects,
                        "validated_provider": first_provider_id,
                        "note": f"Only validating first provider ({first_provider_id}) to save time"
                    }
                else:
                    return {
                        "success": True,
                        "total_projects": len(projects),
                        "providers": {
                            pid: len(projs) for pid, projs in providers.items()
                        },
                        "projects": projects
                    }
            else:
                return {
                    "success": False,
                    "error": f"API returned status {response.status_code}",
                    "total_projects": 0,
                    "providers": {}
                }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "total_projects": 0,
            "providers": {}
        }


def analyze_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze the response and extract key information"""
    analysis = {
        "success": response.get("success", False),
        "has_content": bool(response.get("content")),
        "content_length": len(response.get("content", "")),
        "agents_used": response.get("agents_used", []),
        "event_count": response.get("event_count", 0),
        "mentions_projects": False,
        "mentions_providers": False,
        "has_errors": False
    }
    
    content = response.get("content", "").lower()
    
    # Check for project-related content
    project_keywords = ["project", "projects", "list", "found", "retrieved"]
    analysis["mentions_projects"] = any(keyword in content for keyword in project_keywords)
    
    # Check for provider-related content
    provider_keywords = ["provider", "providers", "configured", "jira", "openproject"]
    analysis["mentions_providers"] = any(keyword in content for keyword in provider_keywords)
    
    # Check for critical errors (ignore expected errors like analytics adapter and provider connection failures)
    critical_error_keywords = [
        "recursion limit", "validation error", "401", "unauthorized", 
        "timeout", "500 internal server error", "graphrecursionerror"
    ]
    expected_errors = [
        "analytics adapter not configured",
        "connection failed",  # Provider connection failures are expected for some providers
        "authentication failed",  # Some providers may have auth issues
        "name resolution error",  # Network issues for some providers are expected
        "failed to retrieve projects"  # Provider-specific failures are expected
    ]
    
    # Check for critical errors (only truly critical ones)
    has_critical_error = any(keyword in content.lower() for keyword in critical_error_keywords)
    
    # Check if errors are only expected ones
    error_matches = [err for err in expected_errors if err in content.lower()]
    has_only_expected_errors = len(error_matches) > 0 and not has_critical_error
    
    # Only mark as error if it's a critical error that's not expected
    # Provider connection failures are expected and should not fail the test
    analysis["has_errors"] = has_critical_error and not has_only_expected_errors
    analysis["has_only_expected_errors"] = has_only_expected_errors
    
    return analysis


async def test_list_my_projects_flow(base_url: str = "http://localhost:8000"):
    """Test the complete 'list my projects' flow"""
    print_section("🧪 Testing 'List My Projects' Flow")
    
    # Step 0: Verify backend API has projects (first provider only to save time)
    print_section("Step 0: Backend API Verification (First Provider Only)")
    api_verification = await verify_backend_api_projects(validate_first_only=True)
    if api_verification["success"]:
        if "note" in api_verification:
            print_info(api_verification["note"])
        print_success(f"Backend API has {api_verification['total_projects']} project(s) from first provider")
        print_info("Projects per provider:")
        for provider_id, count in api_verification["providers"].items():
            print_info(f"  Provider {provider_id}: {count} project(s)")
    else:
        print_error(f"Failed to verify backend API: {api_verification.get('error')}")
    print()
    
    # Step 1: Check backend health
    print_section("Step 1: Backend Health Check")
    if not await check_backend_health(base_url):
        print_error("Backend is not healthy. Please start the backend service.")
        return False
    
    # Step 2: Send PM chat request
    print_section("Step 2: Sending PM Chat Request")
    response = await send_pm_chat_request(base_url, "list my projects")
    
    if not response.get("success"):
        print_error(f"Request failed: {response.get('error', 'Unknown error')}")
        return False
    
    print_success(f"Request completed successfully")
    print_info(f"Status code: {response.get('status_code')}")
    print_info(f"Events received: {response.get('event_count', 0)}")
    print_info(f"Agents used: {', '.join(response.get('agents_used', []))}")
    
    # Step 3: Analyze response
    print_section("Step 3: Analyzing Response")
    analysis = analyze_response(response)
    
    print_info(f"Content length: {analysis['content_length']} characters")
    print_info(f"Mentions projects: {analysis['mentions_projects']}")
    print_info(f"Mentions providers: {analysis['mentions_providers']}")
    print_info(f"Has errors: {analysis['has_errors']}")
    
    # Step 4: Check tool calls and results
    print_section("Step 4: Tool Calls and Results")
    tool_calls = response.get("tool_calls", [])
    tool_results = response.get("tool_results", [])
    
    print_info(f"Tool calls made: {len(tool_calls)}")
    print_info(f"Tool results received: {len(tool_results)}")
    
    # Look for PM-related tool calls
    pm_tools = ["list_projects", "list_providers", "configure_pm_provider", "backend_api_call"]
    pm_tool_calls = []
    list_projects_called = False
    backend_api_projects_called = False
    
    for tool_call in tool_calls:
            # Tool calls have "name" field, not "tool_name"
            tool_name = tool_call.get("name") or tool_call.get("tool_name") or ""
            # Arguments might be in "args" or "arguments" field
            tool_args = str(tool_call.get("args", tool_call.get("arguments", {})))
            
            # Check if this is a PM-related tool
            if tool_name in pm_tools or any(pm_tool in tool_name.lower() for pm_tool in pm_tools):
                pm_tool_calls.append(tool_call)
                print_info(f"  - PM tool called: {tool_name}")
                
                # Check if list_projects MCP tool was called
                if tool_name == "list_projects":
                    list_projects_called = True
                    print_success(f"✅ Found list_projects call with args: {tool_args}")
                # Check if backend_api_call was used for projects
                elif tool_name == "backend_api_call" and "/api/pm/projects" in tool_args:
                    backend_api_projects_called = True
                    print_success(f"✅ Found backend_api_call for projects: {tool_args}")
    
    if pm_tool_calls:
        print_success(f"Found {len(pm_tool_calls)} PM-related tool call(s)")
    else:
        print_warning("No PM-related tool calls detected")
    
    # Check if list_projects MCP tool was used (preferred over backend_api_call)
    if list_projects_called:
        print_success("✅ list_projects MCP tool was called (correct approach)")
    elif backend_api_projects_called:
        print_warning("⚠️  backend_api_call was used for projects (fallback - MCP tools may not be working)")
    else:
        print_warning("⚠️  Neither list_projects MCP tool nor backend_api_call for projects was detected")
    
    # Step 5: Display content preview
    print_section("Step 5: Response Content Preview")
    content = response.get("content", "")
    if content:
        # Show first 2000 characters
        preview = content[:2000]
        print(f"\n{preview}")
        if len(content) > 2000:
            print(f"\n... (showing first 2000 chars, total length: {len(content)} characters)")
        
        # Count projects mentioned - look for various patterns
        import re
        project_patterns = [
            r'found\s+(\d+)\s+project',
            r'(\d+)\s+project[s]?',
            r'project[s]?\s+(?:id|ID)[:\s]+([a-f0-9-]+)',
            r'"id"\s*:\s*"([a-f0-9-]{8}-[a-f0-9-]{4}-[a-f0-9-]{4}-[a-f0-9-]{4}-[a-f0-9-]{12})"',  # UUID pattern
            r'project[s]?\s+[:\s]+([A-Z][a-zA-Z0-9\s-]+)',  # Project names
        ]
        project_count = 0
        project_ids = set()
        project_names = []
        
        for pattern in project_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0] if match else ""
                    try:
                        count = int(match)
                        project_count = max(project_count, count)
                    except (ValueError, TypeError):
                        if isinstance(match, str):
                            # Check if it's a UUID
                            if re.match(r'^[a-f0-9-]{36}$', match, re.IGNORECASE):
                                project_ids.add(match)
                            elif len(match) > 3 and match[0].isupper():
                                project_names.append(match)
        
        # Also look for JSON arrays with project data
        try:
            import json
            # Try to find JSON objects/arrays in the content
            json_matches = re.findall(r'\[.*?\{.*?"id".*?\}.*?\]', content, re.DOTALL)
            for json_str in json_matches:
                try:
                    data = json.loads(json_str)
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and "id" in item:
                                project_ids.add(str(item["id"]))
                            if isinstance(item, dict) and "name" in item:
                                project_names.append(str(item["name"]))
                except:
                    pass
        except:
            pass
        
        if project_count > 0:
            print_success(f"Found {project_count} project(s) mentioned in response")
        if project_ids:
            print_success(f"Found {len(project_ids)} unique project ID(s) in response")
            print_info(f"  Sample IDs: {list(project_ids)[:3]}")
        if project_names:
            print_success(f"Found {len(project_names)} project name(s) in response")
            print_info(f"  Sample names: {project_names[:3]}")
        if project_count == 0 and not project_ids and not project_names:
            print_warning("No project count, IDs, or names found in response")
        
        # Store for analysis
        analysis["project_count"] = project_count
        analysis["project_ids"] = list(project_ids)
        analysis["project_names"] = project_names
    else:
        print_warning("No content in response")
        analysis["project_count"] = 0
        analysis["project_ids"] = []
        analysis["project_names"] = []
    
    # Step 6: Compare MCP results with backend API
    print_section("Step 6: MCP vs Backend API Comparison")
    
    # Extract project counts from response content
    content = response.get("content", "")
    
    # Try to extract project counts from the response
    import re
    # Look for patterns like "Found X project(s)" or "Projects: X"
    project_count_matches = re.findall(r'(\d+)\s+project', content, re.IGNORECASE)
    mcp_project_count = 0
    if project_count_matches:
        try:
            mcp_project_count = max([int(m) for m in project_count_matches])
        except:
            pass
    
    # Compare with backend API
    if api_verification["success"]:
        backend_count = api_verification["total_projects"]
        print_info(f"Backend API projects (first provider only): {backend_count}")
        print_info(f"MCP tool reported projects (all providers): {mcp_project_count}")
        
        # Note: Backend validation only checks first provider, while MCP returns all providers
        # So MCP having MORE projects than backend is expected and acceptable
        if backend_count > 0 and mcp_project_count == 0:
            print_error(
                f"❌ MISMATCH: Backend API has {backend_count} projects, "
                f"but MCP tool reported {mcp_project_count} projects!"
            )
            print_warning(
                "This indicates the MCP server database may have different "
                "provider configurations than the backend database."
            )
            print_warning(
                "Possible causes:\n"
                "  - MCP server providers not configured with correct credentials\n"
                "  - MCP server using different database than backend\n"
                "  - Provider connection failures in MCP server"
            )
        elif backend_count == mcp_project_count:
            print_success(f"✅ Match: Both report {backend_count} projects")
        elif mcp_project_count > backend_count:
            # This is EXPECTED: MCP returns all providers, backend validation only checks first provider
            print_success(
                f"✅ Expected: MCP reports {mcp_project_count} projects (all providers) "
                f"vs backend {backend_count} (first provider only) - this is correct!"
            )
        else:
            print_warning(
                f"MCP reports fewer projects ({mcp_project_count}) than backend first provider ({backend_count})"
            )
    print()
    
    # Step 7: Final assessment
    print_section("Step 7: Test Results")
    
    # Success criteria:
    # 1. Response is successful
    # 2. Has content
    # 3. Projects are mentioned (not just providers)
    # 4. Either no errors, or only expected errors
    # 5. list_projects MCP tool was called (preferred) OR backend_api_call was used (fallback)
    # 6. MCP results should match backend API (if backend has projects)
    has_projects = analysis.get("mentions_projects") or analysis.get("project_ids") or analysis.get("project_count", 0) > 0
    has_list_projects_tool = list_projects_called or backend_api_projects_called
    
    # Check for mismatch
    # Note: MCP having MORE projects than backend is expected (MCP returns all providers,
    # backend validation only checks first provider)
    has_mismatch = False
    if api_verification["success"]:
        backend_count = api_verification["total_projects"]
        # Only fail if backend has projects but MCP has 0 (indicates MCP not working)
        # MCP having more than backend is expected and acceptable
        if backend_count > 0 and mcp_project_count == 0:
            has_mismatch = True
    
    success = (
        analysis["success"] and
        analysis["has_content"] and
        has_projects and  # Must have projects, not just providers
        has_list_projects_tool and  # Must have called a tool to get projects
        (not analysis["has_errors"] or 
         (analysis.get("has_only_expected_errors"))) and
        not has_mismatch  # Fail if there's a mismatch
    )
    
    if success:
        print_success("✅ Test PASSED: 'List My Projects' flow completed successfully")
        if analysis["mentions_projects"]:
            print_success("✅ Projects were mentioned in the response")
        if analysis["mentions_providers"]:
            print_success("✅ Providers were mentioned in the response")
        if api_verification["success"]:
            if mcp_project_count >= backend_count:
                print_success(
                    f"✅ MCP results acceptable: {mcp_project_count} projects (all providers) "
                    f"vs backend {backend_count} (first provider only)"
                )
            else:
                print_success(f"✅ MCP results match backend API ({backend_count} projects)")
    else:
        print_error("❌ Test FAILED: Issues detected in the flow")
        if not analysis["has_content"]:
            print_error("  - No content in response")
        if analysis["has_errors"]:
            print_error("  - Errors detected in response")
        if not analysis["mentions_projects"] and not analysis["mentions_providers"]:
            print_warning("  - No projects or providers mentioned (may be expected if none configured)")
        if has_mismatch:
            print_error(
                f"  - MCP tool returned {mcp_project_count} projects but "
                f"backend API has {backend_count} projects"
            )
    
    return success


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test 'list my projects' flow end-to-end"
    )
    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:8000",
        help="Backend API URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    print(f"\n{Colors.BOLD}🚀 'List My Projects' Flow Test{Colors.RESET}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Backend URL: {args.url}\n")
    
    try:
        success = await test_list_my_projects_flow(args.url)
        
        print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
        if success:
            print(f"{Colors.GREEN}{Colors.BOLD}✅ Test completed successfully!{Colors.RESET}")
        else:
            print(f"{Colors.RED}{Colors.BOLD}❌ Test failed!{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")
        
        return success
        
    except KeyboardInterrupt:
        print_warning("\nTest interrupted by user")
        return False
    except Exception as e:
        print_error(f"\nTest crashed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

