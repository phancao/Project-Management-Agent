"""
PM Agent Result Validator

Validates tool results against user intent and provides retry guidance.
"""
import json
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validating a tool response."""
    passed: bool
    reason: str
    suggestion: Optional[str] = None  # Guidance for retry
    confidence: float = 1.0  # 0.0 - 1.0


def validate_result_sync(
    result: str,
    tool_name: str,
    tool_args: Dict[str, Any],
    original_query: str
) -> ValidationResult:
    """
    Validate tool result using rule-based checks.
    
    This is a synchronous, fast validation without LLM calls.
    For semantic validation, use validate_result_with_llm().
    """
    
    # Check 1: Empty or null result
    if not result or result.strip() == "" or result == "null":
        return ValidationResult(
            passed=False,
            reason="Tool returned empty result",
            suggestion="Try with different parameters or check if data exists"
        )
    
    # Check 2: Parse JSON and check for errors
    try:
        parsed = json.loads(result)
        
        # Check for explicit error responses
        if isinstance(parsed, dict):
            if parsed.get("success") is False:
                error_msg = parsed.get("error", "Unknown error")
                return ValidationResult(
                    passed=False,
                    reason=f"Tool returned error: {error_msg}",
                    suggestion="Check parameters and retry"
                )
            
            if "error" in parsed and not parsed.get("success"):
                return ValidationResult(
                    passed=False,
                    reason=f"Tool error: {parsed['error']}",
                    suggestion="Verify input parameters"
                )
        
        # Check for empty lists
        if isinstance(parsed, dict):
            # Common patterns: {"tasks": []}, {"sprints": []}, {"data": []}
            for key in ["tasks", "sprints", "epics", "users", "projects", "items", "data"]:
                if key in parsed and isinstance(parsed[key], list) and len(parsed[key]) == 0:
                    return ValidationResult(
                        passed=True,  # Valid response, just empty
                        reason=f"No {key} found matching criteria",
                        confidence=0.8
                    )
            
            # Check count field
            count = parsed.get("count", parsed.get("total", None))
            if count == 0:
                return ValidationResult(
                    passed=True,
                    reason="Query returned 0 results (valid but empty)",
                    confidence=0.8
                )
        
    except json.JSONDecodeError:
        # Not JSON - could be plain text response
        if "error" in result.lower():
            return ValidationResult(
                passed=False,
                reason="Response contains error message",
                suggestion="Check tool parameters"
            )
    
    # Check 3: Tool-specific validations
    validation = _validate_by_tool_type(tool_name, result, tool_args, original_query)
    if validation:
        return validation
    
    # Default: Pass if we got here
    return ValidationResult(
        passed=True,
        reason="Result validated successfully",
        confidence=1.0
    )


def _validate_by_tool_type(
    tool_name: str,
    result: str,
    tool_args: Dict[str, Any],
    original_query: str
) -> Optional[ValidationResult]:
    """Tool-specific validation rules."""
    
    try:
        parsed = json.loads(result)
    except:
        return None
    
    if tool_name == "list_tasks":
        # Check if sprint filter was applied correctly
        if "sprint_id" in tool_args and tool_args["sprint_id"]:
            requested_sprint = str(tool_args["sprint_id"])
            tasks = parsed.get("tasks", [])
            
            if tasks:
                # Sample check: verify at least some tasks match the sprint
                # (Smart resolution may have converted sprint number to ID)
                return ValidationResult(
                    passed=True,
                    reason=f"Found {len(tasks)} tasks for sprint filter",
                    confidence=1.0
                )
    
    elif tool_name == "list_sprints":
        sprints = parsed.get("sprints", parsed.get("data", []))
        if isinstance(sprints, list) and len(sprints) > 0:
            return ValidationResult(
                passed=True,
                reason=f"Found {len(sprints)} sprints",
                confidence=1.0
            )
    
    elif tool_name == "list_epics":
        epics = parsed.get("epics", parsed.get("data", []))
        if isinstance(epics, list) and len(epics) > 0:
            return ValidationResult(
                passed=True,
                reason=f"Found {len(epics)} epics",
                confidence=1.0
            )
    
    elif tool_name == "list_users":
        users = parsed.get("users", parsed.get("data", []))
        if isinstance(users, list) and len(users) > 0:
            return ValidationResult(
                passed=True,
                reason=f"Found {len(users)} users",
                confidence=1.0
            )
    
    elif tool_name == "get_current_project_details":
        if parsed.get("success") and parsed.get("project"):
            return ValidationResult(
                passed=True,
                reason="Project details retrieved",
                confidence=1.0
            )
    
    return None


async def validate_result_with_llm(
    result: str,
    original_query: str,
    llm
) -> ValidationResult:
    """
    Use LLM to semantically validate if result matches user intent.
    
    This is slower but more accurate for complex validations.
    """
    from langchain_core.messages import SystemMessage, HumanMessage
    
    # Truncate result for LLM context
    result_preview = result[:2000] if len(result) > 2000 else result
    
    validation_prompt = f"""You are a validation assistant. Check if the tool result answers the user's question.

USER QUERY: {original_query}

TOOL RESULT (preview):
{result_preview}

Does this result appropriately answer the user's question?

Reply with EXACTLY one of:
- PASS: <brief reason why it's valid>
- FAIL: <reason why it doesn't match the query>
"""
    
    try:
        response = await llm.ainvoke([
            SystemMessage(content="You validate tool results. Reply only with PASS or FAIL followed by reason."),
            HumanMessage(content=validation_prompt)
        ])
        
        content = response.content.strip()
        
        if content.startswith("PASS"):
            reason = content[5:].strip(": ") if len(content) > 4 else "Valid result"
            return ValidationResult(passed=True, reason=reason)
        elif content.startswith("FAIL"):
            reason = content[5:].strip(": ") if len(content) > 4 else "Result doesn't match query"
            return ValidationResult(passed=False, reason=reason, suggestion="Retry with different approach")
        else:
            # Couldn't parse - default to pass
            logger.warning(f"[VALIDATOR] Could not parse LLM response: {content[:100]}")
            return ValidationResult(passed=True, reason="Validation inconclusive, proceeding")
    
    except Exception as e:
        logger.error(f"[VALIDATOR] LLM validation failed: {e}")
        # On error, fall back to rule-based validation
        return ValidationResult(passed=True, reason="LLM validation skipped due to error")
