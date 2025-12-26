"""
PM Agent Replanner

Decides what to do after each tool result:
- DONE: Result answers the query, proceed to report
- CALL_TOOL: Need to call another tool
- ANALYZE: Need to process/aggregate the data
"""
import json
import logging
from dataclasses import dataclass
from typing import Literal, Optional, List, Dict, Any

logger = logging.getLogger(__name__)

ActionType = Literal["DONE", "CALL_TOOL", "ANALYZE"]


@dataclass
class ReplanDecision:
    """Decision on what to do next after a tool result."""
    action: ActionType
    reason: str
    next_tool: Optional[str] = None  # For CALL_TOOL action
    next_tool_args: Optional[Dict[str, Any]] = None
    analysis_type: Optional[str] = None  # For ANALYZE action: "aggregate", "filter", "summarize"
    confidence: float = 1.0


def decide_next_action_sync(
    result: str,
    tool_name: str,
    tool_args: Dict[str, Any],
    original_query: str,
    step_count: int,
    max_steps: int = 5
) -> ReplanDecision:
    """
    Rule-based decision on what to do next.
    
    Fast path without LLM call for common patterns.
    """
    query_lower = original_query.lower()
    
    # Safety: if we've reached max steps, force DONE
    if step_count >= max_steps:
        return ReplanDecision(
            action="DONE",
            reason=f"Reached maximum {max_steps} steps, finalizing",
            confidence=0.8
        )
    
    # Pattern 1: Simple listing queries are usually DONE after first tool
    simple_patterns = [
        "list tasks", "show tasks", "get tasks",
        "list sprints", "show sprints",
        "list epics", "show epics",
        "list users", "show team", "team members",
        "project details", "project description"
    ]
    
    for pattern in simple_patterns:
        if pattern in query_lower and step_count == 1:
            # Check if query doesn't ask for additional analysis
            analysis_keywords = ["analyze", "analyse", "who", "overload", "summary", "summarize", "compare", "trend"]
            if not any(kw in query_lower for kw in analysis_keywords):
                return ReplanDecision(
                    action="DONE",
                    reason="Simple listing query completed",
                    confidence=1.0
                )
    
    # Pattern 2: Query asks for analysis after listing
    if step_count == 1:
        # Check if query needs aggregation/analysis
        if any(word in query_lower for word in ["who is", "who's", "overload", "most", "least", "average", "count", "total"]):
            # Parse result to see what we have
            try:
                parsed = json.loads(result)
                if isinstance(parsed, dict) and ("tasks" in parsed or "data" in parsed):
                    return ReplanDecision(
                        action="ANALYZE",
                        reason="Query requires data analysis after listing",
                        analysis_type="aggregate",
                        confidence=0.9
                    )
            except:
                pass
        
        # Check if query needs multiple data sources
        if "and" in query_lower:
            # Simple heuristic: if query has 'and', might need another tool
            parts = query_lower.split(" and ")
            if len(parts) > 1:
                second_part = parts[1].strip()
                
                # Detect what the second part needs
                if any(word in second_part for word in ["sprint", "sprints"]):
                    if tool_name != "list_sprints":
                        return ReplanDecision(
                            action="CALL_TOOL",
                            reason="Query mentions sprints, need sprint data",
                            next_tool="list_sprints",
                            confidence=0.7
                        )
                
                if any(word in second_part for word in ["epic", "epics"]):
                    if tool_name != "list_epics":
                        return ReplanDecision(
                            action="CALL_TOOL",
                            reason="Query mentions epics, need epic data",
                            next_tool="list_epics",
                            confidence=0.7
                        )
                
                if any(word in second_part for word in ["user", "team", "member", "who"]):
                    if tool_name != "list_users":
                        return ReplanDecision(
                            action="CALL_TOOL",
                            reason="Query mentions team/users, need user data",
                            next_tool="list_users",
                            confidence=0.7
                        )
    
    # Pattern 3: After analysis step, usually DONE
    if step_count >= 2:
        return ReplanDecision(
            action="DONE",
            reason="Analysis complete, ready to report",
            confidence=0.9
        )
    
    # Default: DONE
    return ReplanDecision(
        action="DONE",
        reason="No further action needed",
        confidence=0.8
    )


async def decide_next_action_with_llm(
    result: str,
    tool_name: str,
    original_query: str,
    available_tools: List[str],
    llm,
    step_count: int,
    max_steps: int = 5
) -> ReplanDecision:
    """
    Use LLM to decide what to do next.
    
    More accurate but slower - use for complex queries.
    """
    from langchain_core.messages import SystemMessage, HumanMessage
    
    # Safety check
    if step_count >= max_steps:
        return ReplanDecision(
            action="DONE",
            reason=f"Reached maximum {max_steps} steps",
            confidence=1.0
        )
    
    # Truncate result for context
    result_preview = result[:3000] if len(result) > 3000 else result
    
    replan_prompt = f"""You are a planning assistant for a PM agent.

ORIGINAL USER QUERY: {original_query}

LAST TOOL CALLED: {tool_name}
TOOL RESULT (preview):
{result_preview}

AVAILABLE TOOLS: {available_tools}

CURRENT STEP: {step_count} of {max_steps}

Based on the result, what should we do next?

Reply with EXACTLY one of:
- DONE: <reason> - if the result answers the user's query
- CALL_TOOL: <tool_name> - if we need to call another tool (specify which)
- ANALYZE: <type> - if we need to process the data (type: aggregate, filter, summarize)

Be concise. Only reply with one line.
"""
    
    try:
        response = await llm.ainvoke([
            SystemMessage(content="You decide the next action for a PM agent. Reply with DONE, CALL_TOOL, or ANALYZE."),
            HumanMessage(content=replan_prompt)
        ])
        
        content = response.content.strip().upper()
        
        if content.startswith("DONE"):
            reason = response.content.strip()[5:].strip(": ")
            return ReplanDecision(action="DONE", reason=reason or "Query answered")
        
        elif content.startswith("CALL_TOOL"):
            # Extract tool name
            parts = response.content.strip().split(":", 1)
            if len(parts) > 1:
                tool_hint = parts[1].strip().lower()
                # Match to available tools
                for tool in available_tools:
                    if tool.lower() in tool_hint or tool_hint in tool.lower():
                        return ReplanDecision(
                            action="CALL_TOOL",
                            reason=f"Need additional data from {tool}",
                            next_tool=tool
                        )
            return ReplanDecision(action="DONE", reason="Could not determine next tool")
        
        elif content.startswith("ANALYZE"):
            parts = response.content.strip().split(":", 1)
            analysis_type = parts[1].strip().lower() if len(parts) > 1 else "aggregate"
            return ReplanDecision(
                action="ANALYZE",
                reason="Data needs analysis",
                analysis_type=analysis_type
            )
        
        else:
            # Default to DONE if can't parse
            logger.warning(f"[REPLANNER] Could not parse response: {content[:100]}")
            return ReplanDecision(action="DONE", reason="Proceeding with current result")
    
    except Exception as e:
        logger.error(f"[REPLANNER] LLM error: {e}")
        return ReplanDecision(action="DONE", reason="Error in replanning, using current result")


def analyze_result(
    result: str,
    original_query: str,
    analysis_type: str
) -> str:
    """
    Perform analysis on tool result.
    
    Returns analyzed/aggregated result.
    """
    query_lower = original_query.lower()
    
    try:
        parsed = json.loads(result)
    except:
        return result  # Can't analyze non-JSON
    
    if analysis_type == "aggregate":
        # Common aggregation: count by field
        if isinstance(parsed, dict):
            tasks = parsed.get("tasks", parsed.get("data", []))
            
            if tasks and isinstance(tasks, list):
                # Aggregate by assignee if query mentions workload/who
                if any(word in query_lower for word in ["who", "overload", "assignee", "assigned"]):
                    assignee_counts: Dict[str, int] = {}
                    for task in tasks:
                        assignee = task.get("assignee") or task.get("assignee_name") or "Unassigned"
                        if isinstance(assignee, dict):
                            assignee = assignee.get("name", "Unassigned")
                        assignee_counts[assignee] = assignee_counts.get(assignee, 0) + 1
                    
                    # Sort by count descending
                    sorted_counts = sorted(assignee_counts.items(), key=lambda x: x[1], reverse=True)
                    
                    analysis = {
                        "analysis_type": "workload_by_assignee",
                        "total_tasks": len(tasks),
                        "workload": [{"assignee": a, "task_count": c} for a, c in sorted_counts],
                        "most_loaded": sorted_counts[0] if sorted_counts else None
                    }
                    return json.dumps(analysis, indent=2)
                
                # Aggregate by status
                if any(word in query_lower for word in ["status", "progress", "done", "pending"]):
                    status_counts: Dict[str, int] = {}
                    for task in tasks:
                        status = task.get("status", "Unknown")
                        status_counts[status] = status_counts.get(status, 0) + 1
                    
                    analysis = {
                        "analysis_type": "status_breakdown",
                        "total_tasks": len(tasks),
                        "by_status": status_counts
                    }
                    return json.dumps(analysis, indent=2)
    
    elif analysis_type == "summarize":
        # Create a summary
        if isinstance(parsed, dict):
            items = parsed.get("tasks", parsed.get("sprints", parsed.get("epics", parsed.get("data", []))))
            if isinstance(items, list):
                return json.dumps({
                    "summary": f"Found {len(items)} items",
                    "count": len(items)
                })
    
    # Default: return original
    return result
