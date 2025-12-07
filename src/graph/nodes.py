# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import asyncio
import copy
import json
import logging
import os
import re
import time
from functools import partial
from typing import Annotated, Any, Literal

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
import uuid
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.types import Command, interrupt

from src.agents import create_agent
from src.config.agents import AGENT_LLM_MAP
from src.config.configuration import Configuration
from src.llms.llm import get_llm_by_type, get_llm_token_limit_by_type
from src.prompts.planner_model import Plan
from src.prompts.template import apply_prompt_template
from src.tools import (
    crawl_tool,
    backend_api_call,
    get_retriever_tool,
    get_web_search_tool,
    python_repl_tool,
)
from src.tools.search import LoggedTavilySearch
from src.utils.context_manager import ContextManager, validate_message_content
from src.utils.json_utils import repair_json_output, sanitize_tool_response

from ..config import SELECTED_SEARCH_ENGINE, SearchEngine
from .types import State
from .utils import (
    build_clarified_topic_from_history,
    get_message_content,
    reconstruct_clarification_history,
)
from .thought_extractor import (
    attach_thoughts_to_message,
    get_thoughts_from_message,
    merge_thoughts,
    create_thought,
)

logger = logging.getLogger(__name__)


def _add_context_optimization_tool_call(state: State, agent_name: str, optimization_metadata: dict) -> list:
    """
    Create context optimization tool call messages.
    
    Args:
        state: The state (for reference, not modified)
        agent_name: Name of the agent performing optimization
        optimization_metadata: Metadata from compress_messages() containing optimization details
    
    Returns:
        List of messages (AIMessage with tool call + ToolMessage with result) to add to state
    """
    # Always add tool call if optimization metadata exists (even if no compression happened)
    # This shows users that context optimization was attempted
    if not optimization_metadata:
        return []
    
    tool_call_id = f"context_opt_{uuid.uuid4().hex[:8]}"
    
    # Create tool call result message
    original_tokens = optimization_metadata.get("original_tokens", 0)
    compressed_tokens = optimization_metadata.get("compressed_tokens", 0)
    compression_ratio = optimization_metadata.get("compression_ratio", 1.0)
    strategy = optimization_metadata.get("strategy", "unknown")
    original_count = optimization_metadata.get("original_message_count", 0)
    compressed_count = optimization_metadata.get("compressed_message_count", 0)
    
    reduction_pct = (1.0 - compression_ratio) * 100
    was_compressed = optimization_metadata.get("compressed", False)
    
    if was_compressed:
        result_text = (
            f"Context optimized: {original_tokens:,} → {compressed_tokens:,} tokens "
            f"({reduction_pct:.1f}% reduction)\n"
            f"Messages: {original_count} → {compressed_count}\n"
            f"Strategy: {strategy}"
        )
    else:
        result_text = (
            f"Context checked: {original_tokens:,} tokens (within limit, no compression needed)\n"
            f"Messages: {original_count}\n"
            f"Strategy: {strategy}"
        )
    
    # Create tool call result message
    tool_call_message = ToolMessage(
        content=result_text,
        tool_call_id=tool_call_id,
        name="optimize_context"
    )
    
    # Create AIMessage with tool call
    tool_call_aimessage = AIMessage(
        content="",
        name=agent_name,
        tool_calls=[{
            "id": tool_call_id,
            "name": "optimize_context",
            "args": {
                "original_tokens": original_tokens,
                "compressed_tokens": compressed_tokens,
                "compression_ratio": compression_ratio,
                "strategy": strategy,
                "original_message_count": original_count,
                "compressed_message_count": compressed_count
            }
        }]
    )
    
    logger.info(
        f"[{agent_name}] Created context optimization tool call: "
        f"{original_tokens:,} → {compressed_tokens:,} tokens ({reduction_pct:.1f}% reduction)"
    )
    
    return [tool_call_aimessage, tool_call_message]


def detect_user_needs_more_detail(messages: list) -> bool:
    """
    Detects if user is not satisfied with previous answer and wants more detail.
    
    Returns True if:
    - User expresses dissatisfaction
    - User requests more detail/depth
    - User asks follow-up questions indicating incomplete answer
    """
    if len(messages) < 2:
        return False
    
    # Get last user message
    last_user_message = None
    for msg in reversed(messages):
        # Check both dict format and Message objects
        role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "type", None)
        if role == "user" or role == "human":
            content = get_message_content(msg)
            if content:
                last_user_message = content
                break
    
    if not last_user_message:
        return False
    
    msg_lower = last_user_message.lower()
    
    # Fast heuristic patterns
    escalation_patterns = [
        # More detail requests
        "more detail", "not enough", "incomplete", "need more",
        "can you elaborate", "expand on", "tell me more",
        "need comprehensive", "need detailed", "need full",
        
        # Dissatisfaction
        "not what i wanted", "not helpful", "not sufficient",
        "missing", "didn't answer", "not complete",
        
        # Request for deeper analysis
        "comprehensive", "detailed", "full analysis",
        "deeper", "thorough", "complete",
        "in depth", "detailed breakdown",
        
        # With specific additions
        "with charts", "with analysis", "with trends",
        "with recommendations", "with breakdown",
        "step by step", "detailed report",
        
        # Follow-up depth indicators
        "why", "how come", "what about",
        "what if", "can you also", "additionally"
    ]
    
    # Check for clear indicators
    if any(pattern in msg_lower for pattern in escalation_patterns):
        logger.info(f"[FEEDBACK-DETECT] User needs more detail (pattern match)")
        return True
    
    # Check message length - very short messages likely satisfied ("thanks", "ok")
    if len(last_user_message) < 20:
        return False
    
    # For longer ambiguous messages, use LLM classification
    return detect_escalation_with_llm(last_user_message)


def detect_escalation_with_llm(message: str) -> bool:
    """
    Use LLM to detect if user needs escalation to more detailed analysis.
    Fast single call for ambiguous cases.
    """
    try:
        prompt = f"""Analyze if this user message indicates they want MORE DETAIL or are SATISFIED.

Context: User just received a quick answer to their query.

User's response: "{message}"

Does the user want:
- MORE DETAIL / COMPREHENSIVE ANALYSIS (not satisfied with quick answer)
- OR is SATISFIED with the answer?

Respond with ONLY one word: MORE or SATISFIED"""

        llm = get_llm_by_type("basic")
        response = llm.invoke(prompt)
        
        result = "MORE" in response.content.upper()
        logger.info(f"[FEEDBACK-DETECT] LLM classification: {'MORE' if result else 'SATISFIED'}")
        return result
        
    except Exception as e:
        logger.error(f"[FEEDBACK-DETECT] LLM classification failed: {e}")
        # Conservative: don't escalate on error
        return False


def extract_project_id(text: str) -> str:
    """
    Extract project_id from text.
    
    Looks for patterns like:
    - project_id: <id>
    - project_id=<id>
    - project: <id>
    
    Returns empty string if not found.
    """
    if not text:
        return ""
    
    # Try different patterns
    patterns = [
        r'project_id:\s*([^\s\n]+)',
        r'project_id=([^\s\n]+)',
        r'project:\s*([^\s\n]+)',
        r'project=([^\s\n]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            project_id = match.group(1).strip()
            logger.info(f"Extracted project_id: {project_id}")
            return project_id
    
    return ""


@tool
def handoff_to_planner(
    research_topic: Annotated[str, "The topic of the research task to be handed off."],  # noqa: ARG001
    locale: Annotated[str, "The user's detected language locale (e.g., en-US, zh-CN)."],  # noqa: ARG001
):
    """Handoff to planner agent to do plan."""
    # This tool is not returning anything: we're just using it
    # as a way for LLM to signal that it needs to hand off to planner agent
    return


@tool
def handoff_after_clarification(
    locale: Annotated[str, "The user's detected language locale (e.g., en-US, zh-CN)."],  # noqa: ARG001
    research_topic: Annotated[
        str, "The clarified research topic based on all clarification rounds."
    ],  # noqa: ARG001
):
    """Handoff to planner after clarification rounds are complete. Pass all clarification history to planner for analysis."""
    return


def needs_clarification(state: dict) -> bool:
    """
    Check if clarification is needed based on current state.
    Centralized logic for determining when to continue clarification.
    """
    if not state.get("enable_clarification", False):
        return False

    clarification_rounds = state.get("clarification_rounds", 0)
    is_clarification_complete = state.get("is_clarification_complete", False)
    max_clarification_rounds = state.get("max_clarification_rounds", 3)

    # Need clarification if: enabled + has rounds + not complete + not exceeded max
    # Use <= because after asking the Nth question, we still need to wait for the Nth answer
    return (
        clarification_rounds > 0
        and not is_clarification_complete
        and clarification_rounds <= max_clarification_rounds
    )


def validate_and_fix_plan(plan: dict, enforce_web_search: bool = False) -> dict:
    """
    Validate and fix a plan to ensure it meets requirements.

    Args:
        plan: The plan dict to validate
        enforce_web_search: If True, ensure at least one step has need_search=true

    Returns:
        The validated/fixed plan dict
    """
    if not isinstance(plan, dict):
        return plan

    steps = plan.get("steps", [])

    # ============================================================
    # SECTION 1: Repair missing step_type fields (Issue #650 fix)
    # ============================================================
    for idx, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        
        # Check if step_type is missing or empty
        if "step_type" not in step or not step.get("step_type"):
            # Infer step_type based on need_search value
            inferred_type = "research" if step.get("need_search", False) else "processing"
            step["step_type"] = inferred_type
            logger.info(
                f"Repaired missing step_type for step {idx} ({step.get('title', 'Untitled')}): "
                f"inferred as '{inferred_type}' based on need_search={step.get('need_search', False)}"
            )

    # ============================================================
    # SECTION 2: Validate analysis plan completeness (configuration-based)
    # ============================================================
    from src.graph.analysis_types import validate_analysis_plan, AnalysisType, get_required_tools
    
    _is_valid, analysis_type, missing_tools = validate_analysis_plan(plan, steps)
    
    if analysis_type and analysis_type != AnalysisType.UNKNOWN:
        logger.info(
            f"[VALIDATION] Detected analysis type: {analysis_type.value} "
            f"(title: '{plan.get('title', 'N/A')}')"
        )
        
        if missing_tools:
            logger.warning(
                f"[VALIDATION] {analysis_type.value.capitalize()} analysis plan missing {len(missing_tools)} required tools: {', '.join(missing_tools)}"
            )
            logger.warning(
                f"[VALIDATION] Plan title: {plan.get('title', 'N/A')}, "
                f"Steps: {len(steps)}, "
                f"Step types: {[s.get('step_type', 'N/A') for s in steps]}"
            )
            
            # Try to enhance the first pm_query step with missing tools
            for step in steps:
                if step.get("step_type") == "pm_query":
                    current_desc = step.get("description", "")
                    if missing_tools:
                        missing_list = ", ".join(missing_tools)
                        required_count = len(get_required_tools(analysis_type))
                        enhanced_desc = (
                            f"{current_desc}\n\n"
                            f"⚠️ MISSING TOOLS DETECTED: For {analysis_type.value} analysis, "
                            f"you must also call these tools: {missing_list}. "
                            f"Call ALL {required_count} required tools for {analysis_type.value} analysis."
                        )
                        step["description"] = enhanced_desc
                        logger.info(
                            f"[VALIDATION] Enhanced step '{step.get('title', 'N/A')}' description "
                            f"with missing tools reminder for {analysis_type.value} analysis"
                        )
                    break
        else:
            logger.info(
                f"[VALIDATION] {analysis_type.value.capitalize()} analysis plan is complete - all required tools present"
            )

    # ============================================================
    # SECTION 3: Enforce web search requirements
    # ============================================================
    if enforce_web_search:
        # Check if any step has need_search=true
        has_search_step = any(step.get("need_search", False) for step in steps)

        if not has_search_step and steps:
            # Ensure first research step has web search enabled
            for idx, step in enumerate(steps):
                if step.get("step_type") == "research":
                    step["need_search"] = True
                    logger.info(f"Enforced web search on research step at index {idx}")
                    break
            else:
                # Fallback: If no research step exists, convert the first step to a research step with web search enabled.
                # This ensures that at least one step will perform a web search as required.
                steps[0]["step_type"] = "research"
                steps[0]["need_search"] = True
                logger.info(
                    "Converted first step to research with web search enforcement"
                )
        elif not has_search_step and not steps:
            # Add a default research step if no steps exist
            logger.warning("Plan has no steps. Adding default research step.")
            plan["steps"] = [
                {
                    "need_search": True,
                    "title": "Initial Research",
                    "description": "Gather information about the topic",
                    "step_type": "research",
                }
            ]

    return plan


def background_investigation_node(state: State, config: RunnableConfig):
    logger.info("background investigation node is running.")
    configurable = Configuration.from_runnable_config(config)
    query = state.get("clarified_research_topic") or state.get("research_topic")
    background_investigation_results: list[str] = []
    
    # Use get_web_search_tool() which handles provider selection and fallback to DuckDuckGo
    try:
        search_tool = get_web_search_tool(
            configurable.max_search_results,
            provider_id=configurable.search_provider
        )
        searched_content = search_tool.invoke(query or "")
        
        # check if the searched_content is a tuple, then we need to unpack it
        if isinstance(searched_content, tuple):
            searched_content = searched_content[0]
        
        # Handle string JSON response (from Tavily or other tools)
        if isinstance(searched_content, str):
            try:
                parsed = json.loads(searched_content)
                if isinstance(parsed, dict) and "error" in parsed:
                    logger.error(f"Search error: {parsed['error']}")
                    background_investigation_results = []
                elif isinstance(parsed, list):
                    background_investigation_results = [
                        f"## {elem.get('title', 'Untitled')}\n\n{elem.get('content', 'No content')}" 
                        for elem in parsed
                    ]
                else:
                    logger.error(f"Unexpected search response format: {searched_content}")
                    background_investigation_results = []
            except json.JSONDecodeError:
                # If it's not JSON, treat it as plain text (e.g., DuckDuckGo results)
                logger.debug(f"Search returned plain text (not JSON): {searched_content[:100]}...")
                background_investigation_results = [searched_content]
        # Handle legacy list format
        elif isinstance(searched_content, list):
            background_investigation_results = [
                f"## {elem.get('title', 'Untitled')}\n\n{elem.get('content', 'No content')}" 
                if isinstance(elem, dict) else str(elem)
                for elem in searched_content
            ]
        else:
            logger.error(
                f"Search returned malformed response: {type(searched_content)}"
            )
            background_investigation_results = []
    except Exception as e:
        logger.error(f"Error in background investigation search: {e}", exc_info=True)
        background_investigation_results = []
    
    # Format results as a single string
    if background_investigation_results:
        results_text = "\n\n".join(background_investigation_results)
    else:
        results_text = ""
    
    return {
        "background_investigation_results": results_text
    }


def planner_node(
    state: State, config: RunnableConfig
) -> Command[Literal["human_feedback", "reporter"]]:
    logger.info(f"[DEBUG-NODES] [NODE-PLANNER-1] Planner node entered")
    """Planner node that generate the full plan."""
    configurable = Configuration.from_runnable_config(config)
    plan_iterations = state["plan_iterations"] if state.get("plan_iterations", 0) else 0
    reflection = state.get("reflection", "")
    
    # Check if this is a replanning iteration
    if reflection and plan_iterations > 0:
        logger.info(f"[PLANNER] Replanning (iteration {plan_iterations}) with reflection context")
    else:
        logger.info("Planner generating full plan")

    # Extract project_id from research topic or messages
    project_id = state.get("project_id", "")
    if not project_id:
        # Try to extract from research_topic
        research_topic = state.get("research_topic", "")
        project_id = extract_project_id(research_topic)
        
        # If not found, try from clarified_research_topic
        if not project_id:
            clarified_topic = state.get("clarified_research_topic", "")
            project_id = extract_project_id(clarified_topic)
        
        # If still not found, try from messages
        if not project_id:
            for msg in state.get("messages", []):
                content = get_message_content(msg)
                if content:
                    project_id = extract_project_id(content)
                    if project_id:
                        break
        
        if project_id:
            import sys
            sys.stderr.write(f"\n📌 EXTRACTED PROJECT_ID: {project_id}\n")
            sys.stderr.flush()

    # Detect if this is a PM query (has project_id or PM-related keywords) for logging
    is_pm_query = False
    pm_query_indicators = []
    if project_id:
        is_pm_query = True
        pm_query_indicators.append(f"project_id: {project_id}")
    
    # Check messages for PM-related keywords
    for msg in state.get("messages", []):
        content = get_message_content(msg)
        if content:
            content_lower = content.lower()
            pm_keywords = [
                # Project analysis
                "project analysis", "comprehensive project", "project status", "project performance", 
                "project health", "project overview", "how is the project",
                # Sprint analysis
                "sprint analysis", "analyze sprint", "analyse sprint", "sprint performance",
                "sprint metrics", "sprint velocity", "sprint report", "sprint [0-9]",
                # Epic analysis
                "epic analysis", "epic progress", "epic status", "analyze epic",
                # Task analysis
                "task analysis", "task completion", "task progress", "task metrics",
                # Resource analysis
                "resource analysis", "resource allocation", "resource assignation", 
                "workload analysis", "team workload", "resource utilization",
                "task statistics", "task distribution",
                # Team metrics
                "team performance", "team velocity", "team metrics", "how is the team",
                # Analytics charts
                "velocity chart", "burndown chart", "burndown analysis", "cfd chart",
                "cycle time", "work distribution", "issue trend", "issue trend analysis",
                # Data queries
                "list tasks", "list sprints", "list projects", "list epics",
                "show tasks", "show sprints", "show projects", "show epics",
                "my tasks", "my projects",
                # Other PM queries
                "comprehensive analysis", "full analysis"
            ]
            found_keywords = [kw for kw in pm_keywords if kw in content_lower]
            if found_keywords:
                is_pm_query = True
                pm_query_indicators.append(f"keywords: {', '.join(found_keywords[:3])}")
                break
    
    # Always use regular planner (it has PM query detection built-in)
    # Log PM query detection for identification
    prompt_template = "planner"
    if is_pm_query:
        logger.info(f"[PLANNER] 🔵 PM QUERY DETECTED - Indicators: {', '.join(pm_query_indicators)}")
        logger.info(f"[PLANNER] Using 'planner' template (has built-in PM query handling)")
    else:
        logger.info(f"[PLANNER] 🔍 Research query detected - Using 'planner' template")
    
    # For clarification feature: use the clarified research topic (complete history)
    if state.get("enable_clarification", False) and state.get(
        "clarified_research_topic"
    ):
        # Modify state to use clarified research topic instead of full conversation
        modified_state = state.copy()
        modified_state["messages"] = [
            {"role": "user", "content": state["clarified_research_topic"]}
        ]
        modified_state["research_topic"] = state["clarified_research_topic"]
        messages = apply_prompt_template(prompt_template, modified_state, configurable, state.get("locale", "en-US"))

        logger.info(
            f"Clarification mode: Using clarified research topic: {state['clarified_research_topic']}"
        )
    else:
        # Normal mode: use full conversation history
        messages = apply_prompt_template(prompt_template, state, configurable, state.get("locale", "en-US"))

    if state.get("enable_background_investigation") and state.get(
        "background_investigation_results"
    ):
        messages += [
            {
                "role": "user",
                "content": (
                    "background investigation results of user query:\n"
                    + state["background_investigation_results"]
                    + "\n"
                ),
            }
        ]
    
    # Add ReAct escalation context if escalating from fast path
    escalation_reason = state.get("escalation_reason", "")
    partial_result = state.get("partial_result", "")
    react_attempts = state.get("react_attempts", [])
    
    if escalation_reason:
        escalation_context = f"""
⚡ **ESCALATION FROM REACT AGENT**

**Reason:** {escalation_reason}

**What happened:**
The fast ReAct agent attempted to handle this query but encountered issues:
- Iterations: {len(react_attempts)}
- Partial result: {partial_result[:300] if partial_result else 'None'}

**Your task:**
Create a comprehensive plan that addresses the user's query with proper multi-step execution.
Learn from the ReAct agent's attempts and create a better strategy.
"""
        
        # Add observations from React attempts if available
        if react_attempts and len(react_attempts) > 0:
            escalation_context += "\n**ReAct Agent's Observations:**\n"
            for idx, attempt in enumerate(react_attempts[:3]):  # Show first 3 attempts
                if len(attempt) > 1:
                    action = str(attempt[0])[:100] if attempt[0] else ""
                    observation = str(attempt[1])[:200] if attempt[1] else ""
                    escalation_context += f"{idx + 1}. Action: {action}\n   Observation: {observation}\n\n"
        
        messages += [
            {
                "role": "user",
                "content": escalation_context
            }
        ]
        
        logger.info(f"[PLANNER] Added ReAct escalation context (reason: {escalation_reason})")
    
    # CRITICAL: Add reflection context if this is a replanning iteration
    if reflection and plan_iterations > 0:
        previous_plan = state.get("current_plan")
        validation_results = state.get("validation_results", [])
        
        reflection_context = f"""
🔄 **REPLANNING REQUIRED** (Iteration {plan_iterations})

**Previous Plan Failed:**
"""
        if previous_plan and not isinstance(previous_plan, str):
            reflection_context += f"\nTitle: {previous_plan.title}\n"
            reflection_context += f"Thought: {previous_plan.thought}\n\n"
            reflection_context += "Steps executed:\n"
            for idx, step in enumerate(previous_plan.steps):
                status = "✅ Completed" if step.execution_res else "⏸️ Pending"
                reflection_context += f"{idx + 1}. {step.title} - {status}\n"
                if step.execution_res and len(str(step.execution_res)) > 0:
                    # Show first 200 chars of result
                    result_preview = str(step.execution_res)[:200]
                    if "[ERROR]" in result_preview or "Error" in result_preview:
                        reflection_context += f"   ❌ Error: {result_preview}...\n"
        
        reflection_context += f"\n**Failure Analysis (Reflection):**\n{reflection}\n"
        
        if validation_results:
            failed_validations = [v for v in validation_results if v.get("status") == "failure"]
            if failed_validations:
                reflection_context += "\n**Failed Validations:**\n"
                for v in failed_validations:
                    reflection_context += f"- Step: {v.get('step_title')}\n"
                    reflection_context += f"  Reason: {v.get('reason')}\n"
                    if v.get("suggested_fix"):
                        reflection_context += f"  Suggested Fix: {v.get('suggested_fix')}\n"
        
        reflection_context += """

**Instructions for New Plan:**
1. Address the issues identified in the reflection
2. Use a different approach or break down steps differently
3. Add validation or error handling steps if needed
4. Consider dependencies between steps
5. Be more specific in step descriptions to avoid ambiguity

Create a NEW plan that learns from these failures."""

        messages += [
            {
                "role": "user",
                "content": reflection_context
            }
        ]
        
        logger.debug(f"[PLANNER] Added reflection context ({len(reflection_context)} chars)")

    # if the plan iterations is greater than the max plan iterations, return the reporter node
    if plan_iterations >= configurable.max_plan_iterations:
        return Command(goto="reporter")

    full_response = ""
    
    if configurable.enable_deep_thinking:
        # Deep thinking mode - use reasoning LLM
        llm = get_llm_by_type("reasoning")
        logger.info("[PLANNER] 📨 Using reasoning LLM (LangGraph will stream)")
        response = llm.invoke(messages)
        full_response = response.content if hasattr(response, 'content') else str(response)
    else:
        # Standard mode - use basic LLM with streaming
        # We DON'T use structured output here because it prevents streaming
        # Instead, we'll parse the JSON response manually
        llm = get_llm_by_type("basic")
        logger.info("[PLANNER] 📨 Using basic LLM invoke (LangGraph will stream)")
        
        try:
            response = llm.invoke(messages)
            full_response = response.content if hasattr(response, 'content') else str(response)
            logger.info(f"[PLANNER] 📨 LLM response received, length={len(full_response)}")
        except Exception as e:
            logger.error(f"[PLANNER] LLM invocation failed: {e}")
            if plan_iterations > 0:
                return Command(goto="reporter")
            else:
                return Command(goto="__end__")
    logger.debug(f"Current state messages: {state['messages']}")
    logger.info(f"Planner response: {full_response}")

    try:
        curr_plan = json.loads(repair_json_output(full_response))
    except json.JSONDecodeError:
        logger.warning("Planner response is not a valid JSON")
        if plan_iterations > 0:
            return Command(goto="reporter")
        else:
            return Command(goto="__end__")

    # Log plan step types for identification
    if isinstance(curr_plan, dict) and "steps" in curr_plan:
        step_types = [step.get("step_type", "unknown") for step in curr_plan.get("steps", [])]
        need_search_flags = [step.get("need_search", False) for step in curr_plan.get("steps", [])]
        logger.info(f"[PLANNER] 📋 Generated plan with {len(step_types)} steps")
        logger.info(f"[PLANNER] Step types: {', '.join(step_types)}")
        logger.info(f"[PLANNER] Need search flags: {need_search_flags}")
        
        # Identify if this is a PM plan or research plan
        has_pm_query = any(st == "pm_query" for st in step_types)
        has_research = any(st == "research" for st in step_types)
        has_web_search = any(need_search_flags)
        
        if has_pm_query:
            logger.info(f"[PLANNER] ✅ PM PLAN DETECTED - Contains pm_query steps")
        elif has_research or has_web_search:
            logger.info(f"[PLANNER] 🔍 RESEARCH PLAN DETECTED - Contains research steps or web_search")
        else:
            logger.info(f"[PLANNER] ⚙️  PROCESSING PLAN DETECTED - Contains processing steps")

    # Validate and fix plan to ensure web search requirements are met
    new_plan = None
    if isinstance(curr_plan, dict):
        curr_plan = validate_and_fix_plan(curr_plan, configurable.enforce_web_search)
        
        # Ensure required fields are present before validation
        if "locale" not in curr_plan:
            curr_plan["locale"] = state.get("locale", "en-US")
            logger.info(f"[PLANNER] Added missing locale field: {curr_plan['locale']}")
        
        if "title" not in curr_plan:
            # Generate a default title from steps if available
            if curr_plan.get("steps"):
                curr_plan["title"] = curr_plan["steps"][0].get("title", "Execution Plan")
            else:
                curr_plan["title"] = "Execution Plan"
            logger.info(f"[PLANNER] Added missing title field: {curr_plan['title']}")
        
        # Validate plan structure (even if has_enough_context is False, we still need valid structure)
        try:
            new_plan = Plan.model_validate(curr_plan)
        except Exception as e:
            logger.error(f"[PLANNER] Plan validation failed: {e}")
            logger.error(f"[PLANNER] Plan content: {json.dumps(curr_plan, indent=2)}")
            # Try to fix common issues
            if "has_enough_context" not in curr_plan:
                curr_plan["has_enough_context"] = False
            if "thought" not in curr_plan:
                curr_plan["thought"] = curr_plan.get("overall_thought", "")
            try:
                new_plan = Plan.model_validate(curr_plan)
            except Exception as e2:
                logger.error(f"[PLANNER] Plan validation failed again: {e2}")
                # Return to reporter with error
                return Command(goto="reporter")

    if isinstance(curr_plan, dict) and curr_plan.get("has_enough_context") and new_plan:
        logger.info("Planner response has enough context.")
        
        # Check if plan has steps that need execution (e.g., PM tool calls)
        # Even if has_enough_context is true, we need to execute steps first
        if new_plan.steps and len(new_plan.steps) > 0:
            logger.info(
                f"Plan has {len(new_plan.steps)} step(s) to execute. "
                "Routing to research_team before reporting."
            )
            # Route to research_team to execute the plan steps (PM tools, etc.)
            # After execution, research_team will route back to planner/reporter
            return Command(
                update={
                    "messages": [AIMessage(content=full_response, name="planner")],
                    "current_plan": new_plan,
                    "total_steps": len(new_plan.steps),
                    "current_step_index": 0,  # Reset to first step
                    "project_id": project_id,  # Pass project_id to agents
                },
                goto="research_team",
            )
        else:
            # No steps to execute, can go directly to reporter
            logger.info("Plan has no steps to execute. Routing directly to reporter.")
            return Command(
                update={
                    "messages": [AIMessage(content=full_response, name="planner")],
                    "current_plan": new_plan,
                    "total_steps": len(new_plan.steps) if new_plan.steps else 0,
                    "current_step_index": 0,
                    "project_id": project_id,  # Pass project_id to agents
                },
                goto="reporter",
            )
    return Command(
        update={
            "messages": [AIMessage(content=full_response, name="planner")],
            "current_plan": full_response,
            "project_id": project_id,  # Pass project_id to agents
        },
        goto="human_feedback",
    )


def human_feedback_node(
    state: State, config: RunnableConfig
) -> Command[Literal["planner", "research_team", "reporter", "__end__"]]:
    current_plan = state.get("current_plan", "")
    # check if the plan is auto accepted
    auto_accepted_plan = state.get("auto_accepted_plan", False)
    if not auto_accepted_plan:
        feedback = interrupt("Please Review the Plan.")

        # Handle None or empty feedback
        if not feedback:
            logger.warning(f"Received empty or None feedback: {feedback}. Returning to planner for new plan.")
            return Command(goto="planner")

        # Normalize feedback string
        feedback_normalized = str(feedback).strip().upper()

        # if the feedback is not accepted, return the planner node
        if feedback_normalized.startswith("[EDIT_PLAN]"):
            logger.info(f"Plan edit requested by user: {feedback}")
            return Command(
                update={
                    "messages": [
                        HumanMessage(content=feedback, name="feedback"),
                    ],
                },
                goto="planner",
            )
        elif feedback_normalized.startswith("[ACCEPTED]"):
            logger.info("Plan is accepted by user.")
        else:
            logger.warning(f"Unsupported feedback format: {feedback}. Please use '[ACCEPTED]' to accept or '[EDIT_PLAN]' to edit.")
            return Command(goto="planner")

    # if the plan is accepted, run the following node
    plan_iterations = state["plan_iterations"] if state.get("plan_iterations", 0) else 0
    goto = "research_team"
    try:
        current_plan = repair_json_output(current_plan)
        # increment the plan iterations
        plan_iterations += 1
        # parse the plan
        new_plan = json.loads(current_plan)
        # Validate and fix plan to ensure web search requirements are met
        configurable = Configuration.from_runnable_config(config)
        new_plan = validate_and_fix_plan(new_plan, configurable.enforce_web_search)
    except json.JSONDecodeError:
        logger.warning("Planner response is not a valid JSON")
        if plan_iterations > 1:  # the plan_iterations is increased before this check
            return Command(goto="reporter")
        else:
            return Command(goto="__end__")

    validated_plan = Plan.model_validate(new_plan)
    return Command(
        update={
            "current_plan": validated_plan,
            "plan_iterations": plan_iterations,
            "locale": new_plan["locale"],
            "total_steps": len(validated_plan.steps) if validated_plan.steps else 0,
            "current_step_index": 0,  # Reset to first step
        },
        goto=goto,
    )


def coordinator_node(
    state: State, config: RunnableConfig
) -> Command[Literal["planner", "background_investigator", "coordinator", "react_agent", "__end__"]]:
    logger.info(f"[DEBUG-NODES] [NODE-COORD-1] Coordinator node entered")
    logger.info(f"[COORDINATOR] 🚀 COORDINATOR NODE CALLED - State keys: {list(state.keys())}")
    """
    Adaptive coordinator that intelligently routes queries.
    
    Routing logic:
    1. First query → Start with ReAct (optimistic, fast)
    2. Follow-up with "need more detail" → Escalate to planner
    3. Background investigation enabled → Use that flow
    4. Clarification enabled → Use that flow
    """
    logger.info("Coordinator talking.")
    configurable = Configuration.from_runnable_config(config)
    
    # ADAPTIVE ROUTING: Check if user wants more detail (follow-up escalation)
    messages = state.get("messages", [])
    previous_result = state.get("previous_result", None)
    routing_mode = state.get("routing_mode", "")
    
    if previous_result and routing_mode == "react_first":
        # We previously used ReAct fast path, check if user wants more
        logger.info("[COORDINATOR] Checking if user needs escalation from previous ReAct result")
        
        needs_escalation = detect_user_needs_more_detail(messages)
        
        if needs_escalation:
            logger.info("[COORDINATOR] 🔄 USER ESCALATION - User needs more detail, routing to planner")
            
            # Build context for planner
            last_user_msg = get_message_content(messages[-1]) if messages else ""
            escalation_context = f"""
Previous Quick Answer (ReAct):
{previous_result[:500]}...

User Feedback:
"{last_user_msg}"

The user indicated the quick answer was not sufficient. 
Create a comprehensive plan that addresses their need for more detailed analysis.
"""
            
            return Command(
                update={
                    "routing_mode": "user_escalated",
                    "escalation_context": escalation_context,
                    "goto": "planner"  # Must update state to prevent KeyError
                },
                goto="planner"
            )

    # Check if clarification is enabled
    enable_clarification = state.get("enable_clarification", False)
    initial_topic = state.get("research_topic", "")
    clarified_topic = initial_topic
    # ============================================================
    # BRANCH 1: Clarification DISABLED (Legacy Mode)
    # ============================================================
    if not enable_clarification:
        # Use normal prompt with explicit instruction to skip clarification
        messages = apply_prompt_template("coordinator", state, locale=state.get("locale", "en-US"))
        messages.append(
            {
                "role": "system",
                "content": "CRITICAL: Clarification is DISABLED. You MUST immediately call handoff_to_planner tool with the user's query as-is. Do NOT ask questions or mention needing more information.",
            }
        )

        # Only bind handoff_to_planner tool
        tools = [handoff_to_planner]
        response = (
            get_llm_by_type(AGENT_LLM_MAP["coordinator"])
            .bind_tools(tools)
            .invoke(messages)
        )

        goto = "planner"
        locale = state.get("locale", "en-US")
        research_topic = state.get("research_topic", "")

        # Process tool calls for legacy mode
        if response.tool_calls:
            try:
                for tool_call in response.tool_calls:
                    tool_name = tool_call.get("name", "")
                    tool_args = tool_call.get("args", {})

                    if tool_name == "handoff_to_planner":
                        logger.info("Handing off to planner")
                        goto = "planner"

                        # Extract locale and research_topic if provided
                        if tool_args.get("locale") and tool_args.get("research_topic"):
                            locale = tool_args.get("locale")
                            research_topic = tool_args.get("research_topic")
                        break

            except Exception as e:
                logger.error(f"Error processing tool calls: {e}")
                goto = "planner"

    # ============================================================
    # BRANCH 2: Clarification ENABLED (New Feature)
    # ============================================================
    else:
        # Load clarification state
        clarification_rounds = state.get("clarification_rounds", 0)
        clarification_history = list(state.get("clarification_history", []) or [])
        clarification_history = [item for item in clarification_history if item]
        max_clarification_rounds = state.get("max_clarification_rounds", 3)

        # Prepare the messages for the coordinator
        state_messages = list(state.get("messages", []))
        messages = apply_prompt_template("coordinator", state, locale=state.get("locale", "en-US"))

        clarification_history = reconstruct_clarification_history(
            state_messages, clarification_history, initial_topic
        )
        clarified_topic, clarification_history = build_clarified_topic_from_history(
            clarification_history
        )
        logger.debug("Clarification history rebuilt: %s", clarification_history)

        if clarification_history:
            initial_topic = clarification_history[0]
            latest_user_content = clarification_history[-1]
        else:
            latest_user_content = ""

        # Add clarification status for first round
        if clarification_rounds == 0:
            messages.append(
                {
                    "role": "system",
                    "content": "Clarification mode is ENABLED. Follow the 'Clarification Process' guidelines in your instructions.",
                }
            )

        current_response = latest_user_content or "No response"
        logger.info(
            "Clarification round %s/%s | topic: %s | current user response: %s",
            clarification_rounds,
            max_clarification_rounds,
            clarified_topic or initial_topic,
            current_response,
        )

        clarification_context = f"""Continuing clarification (round {clarification_rounds}/{max_clarification_rounds}):
            User's latest response: {current_response}
            Ask for remaining missing dimensions. Do NOT repeat questions or start new topics."""

        messages.append({"role": "system", "content": clarification_context})

        # Bind both clarification tools - let LLM choose the appropriate one
        tools = [handoff_to_planner, handoff_after_clarification]

        # Check if we've already reached max rounds
        if clarification_rounds >= max_clarification_rounds:
            # Max rounds reached - force handoff by adding system instruction
            logger.warning(
                f"Max clarification rounds ({max_clarification_rounds}) reached. Forcing handoff to planner. Using prepared clarified topic: {clarified_topic}"
            )
            # Add system instruction to force handoff - let LLM choose the right tool
            messages.append(
                {
                    "role": "system",
                    "content": f"MAX ROUNDS REACHED. You MUST call handoff_after_clarification (not handoff_to_planner) with the appropriate locale based on the user's language and research_topic='{clarified_topic}'. Do not ask any more questions.",
                }
            )

        response = (
            get_llm_by_type(AGENT_LLM_MAP["coordinator"])
            .bind_tools(tools)
            .invoke(messages)
        )
        logger.debug(f"Current state messages: {state['messages']}")

        # Initialize response processing variables
        goto = "__end__"
        locale = state.get("locale", "en-US")
        research_topic = (
            clarification_history[0]
            if clarification_history
            else state.get("research_topic", "")
        )
        if not clarified_topic:
            clarified_topic = research_topic

        # --- Process LLM response ---
        # No tool calls - LLM is asking a clarifying question
        if not response.tool_calls and response.content:
            # Check if we've reached max rounds - if so, force handoff to planner
            if clarification_rounds >= max_clarification_rounds:
                logger.warning(
                    f"Max clarification rounds ({max_clarification_rounds}) reached. "
                    "LLM didn't call handoff tool, forcing handoff to planner."
                )
                goto = "planner"
                # Continue to final section instead of early return
            else:
                # Continue clarification process
                clarification_rounds += 1
                # Do NOT add LLM response to clarification_history - only user responses
                logger.info(
                    f"Clarification response: {clarification_rounds}/{max_clarification_rounds}: {response.content}"
                )

                # Only collect NEW messages to add (not the entire list to avoid duplicates)
                new_messages = []
                if response.content:
                    new_messages.append(
                        HumanMessage(content=response.content, name="coordinator")
                    )

                update_dict = {
                    "locale": locale,
                    "research_topic": research_topic,
                    "resources": configurable.resources,
                    "clarification_rounds": clarification_rounds,
                    "clarification_history": clarification_history,
                    "clarified_research_topic": clarified_topic,
                    "is_clarification_complete": False,
                    "goto": goto,
                    "__interrupt__": [("coordinator", response.content)],
                }
                # Only add messages if we have new ones (prevents duplicating existing messages)
                if new_messages:
                    update_dict["messages"] = new_messages

                return Command(
                    update=update_dict,
                    goto=goto,
                )
        else:
            # LLM called a tool (handoff) or has no content - clarification complete
            if response.tool_calls:
                logger.info(
                    f"Clarification completed after {clarification_rounds} rounds. LLM called handoff tool."
                )
            else:
                logger.warning("LLM response has no content and no tool calls.")
            # goto will be set in the final section based on tool calls

    # ============================================================
    # Final: Build and return Command
    # ============================================================
    # Only collect NEW messages to add (not the entire list to avoid duplicates)
    new_messages = []
    # Only add coordinator message if response exists (not early return path)
    if 'response' in locals() and response and hasattr(response, 'content') and response.content:
        new_messages.append(HumanMessage(content=response.content, name="coordinator"))

    # Process tool calls for BOTH branches (legacy and clarification)
    # Only process if response exists (not early return path)
    if 'response' in locals() and response and hasattr(response, 'tool_calls') and response.tool_calls:
        try:
            for tool_call in response.tool_calls:
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("args", {})

                if tool_name in ["handoff_to_planner", "handoff_after_clarification"]:
                    logger.info("Handing off to planner")
                    goto = "planner"

                    # Extract locale if provided
                    locale = tool_args.get("locale", locale)
                    if not enable_clarification and tool_args.get("research_topic"):
                        research_topic = tool_args["research_topic"]

                    if enable_clarification:
                        logger.info(
                            "Using prepared clarified topic: %s",
                            clarified_topic or research_topic,
                        )
                    else:
                        logger.info(
                            "Using research topic for handoff: %s", research_topic
                        )
                    break

        except Exception as e:
            logger.error(f"Error processing tool calls: {e}")
            goto = "planner"
    else:
        # No tool calls detected - fallback to planner instead of ending
        logger.warning(
            "LLM didn't call any tools. This may indicate tool calling issues with the model. "
            "Falling back to planner to ensure research proceeds."
        )
        # Log full response for debugging (only if response exists)
        if 'response' in locals() and response:
            logger.debug(f"Coordinator response content: {response.content if hasattr(response, 'content') else 'N/A'}")
            logger.debug(f"Coordinator response object: {response}")
        # Fallback to planner to ensure workflow continues
        goto = "planner"

    # Set default values for state variables (in case they're not defined in legacy mode)
    if not enable_clarification:
        clarification_rounds = 0
        clarification_history = []

    clarified_research_topic_value = clarified_topic or research_topic

    # ============================================================
    # CRITICAL: Extract project_id BEFORE routing
    # ============================================================
    # Extract project_id from state or messages so ReAct agent can use it
    project_id = state.get("project_id", "")
    if not project_id:
        # Try to extract from research_topic
        project_id = extract_project_id(research_topic)
        
        # If not found, try from clarified_research_topic
        if not project_id:
            project_id = extract_project_id(clarified_research_topic_value)
        
        # If still not found, try from messages
        if not project_id:
            for msg in state.get("messages", []):
                content = get_message_content(msg)
                if content:
                    project_id = extract_project_id(content)
                    if project_id:
                        break
        
        if project_id:
            logger.info(f"[COORDINATOR] 📌 Extracted project_id: {project_id}")
    
    # ============================================================
    # ADAPTIVE ROUTING: Apply AFTER all tool call processing
    # ============================================================
    # Strategy:
    # 1. First query → ReAct (fast, has web_search tool for context if needed)
    # 2. User escalation → Full Pipeline (comprehensive analysis)
    # 3. Background investigation is now a TOOL for ReAct, not a separate route
    # ============================================================
    escalation_reason = state.get("escalation_reason", "")
    
    logger.info(f"[COORDINATOR] 🔍 Routing state: goto={goto}, escalation={bool(escalation_reason)}, previous_result={bool(previous_result)}, project_id={project_id if project_id else 'None'}")
    
    # Let React Agent try first for ALL queries (it will escalate if needed)
    # Only skip React Agent if:
    # 1. Already escalated from React Agent (escalation_reason exists)
    # 2. User explicitly requested escalation (previous_result exists)
    if goto == "planner" and not escalation_reason and not previous_result:
        # First-time query → Use ReAct (fast), even for comprehensive queries
        # React Agent will auto-escalate to planner if it can't handle complexity
        logger.info("[COORDINATOR] ⚡ ADAPTIVE ROUTING - Using ReAct fast path (will escalate if needed)")
        goto = "react_agent"
    elif escalation_reason or previous_result:
        # Already tried React Agent or user requested escalation → Use full pipeline
        logger.info(f"[COORDINATOR] 📊 Using full pipeline: escalation={escalation_reason}, previous_result={bool(previous_result)}")
        goto = "planner"
    
    # Final routing decision
    logger.info(f"[COORDINATOR] 🎯 FINAL DECISION: {goto}")

    # clarified_research_topic: Complete clarified topic with all clarification rounds
    # Only include messages in update if we have new messages to add (prevents duplicates)
    update_dict = {
        "locale": locale,
        "research_topic": research_topic,
        "clarified_research_topic": clarified_research_topic_value,
        "resources": configurable.resources,
        "clarification_rounds": clarification_rounds,
        "clarification_history": clarification_history,
        "is_clarification_complete": goto != "coordinator",
        "goto": goto,
        "routing_mode": "react_first" if goto == "react_agent" else "",
    }
    # CRITICAL: Include project_id in state so ReAct agent can use it
    if project_id:
        update_dict["project_id"] = project_id
        logger.info(f"[COORDINATOR] ✅ Passing project_id to {goto}: {project_id}")
    # Only add messages if we have new ones (prevents duplicating existing messages)
    if new_messages:
        update_dict["messages"] = new_messages
    
    return Command(
        update=update_dict,
        goto=goto,
    )


def reporter_node(state: State, config: RunnableConfig):
    logger.info(f"[DEBUG-NODES] [NODE-REPORTER-1] Reporter node entered")
    """Reporter node that write a final report."""
    
    # CRITICAL: Check if reporter already completed (prevent infinite loop)
    if state.get("final_report"):
        logger.warning("[REPORTER] 🚨 CRITICAL: Reporter already completed (final_report exists). Skipping execution to prevent duplicate reports.")
        # Return the existing report without re-executing
        return Command(
            update={},  # No state changes
            goto="__end__"  # Route to END to stop the workflow
        )
    
    logger.info("Reporter write final report")
    configurable = Configuration.from_runnable_config(config)
    current_plan = state.get("current_plan")
    
    # CRITICAL: If this is coming from React Agent (not planner), use the actual user query
    # React Agent routes to reporter with routing_mode="react_first" and doesn't create a plan
    # In this case, we should use the research_topic or the actual user query instead of plan title
    routing_mode = state.get("routing_mode", "")
    is_from_react = routing_mode == "react_first"
    
    if is_from_react:
        # Coming from React Agent - use the actual user query
        research_topic = state.get("research_topic") or state.get("clarified_research_topic", "")
        # Also try to get from messages if research_topic is empty
        if not research_topic:
            messages = state.get("messages", [])
            for msg in messages:
                if hasattr(msg, 'content') and msg.content:
                    content = str(msg.content)
                    # Skip system messages and tool messages
                    if not content.startswith("#") and "Tool:" not in content:
                        research_topic = content[:500]  # Limit length
                        break
        
        plan_title = research_topic if research_topic else "User Query"
        plan_thought = ""
        logger.info(f"[REPORTER] 🔍 Detected React Agent route - using user query as task: {plan_title[:100]}")
    else:
        # Coming from planner - use plan title as before
        # Handle case where current_plan might be a string (legacy) or None
        if isinstance(current_plan, str):
            plan_title = current_plan
            plan_thought = ""
        elif current_plan and hasattr(current_plan, 'title'):
            plan_title = getattr(current_plan, 'title', 'Research Task')
            plan_thought = getattr(current_plan, 'thought', '')
        else:
            plan_title = "Research Task"
            plan_thought = ""
        logger.info(f"[REPORTER] 📋 Using plan title: {plan_title[:100]}")
    
    # CRITICAL: Only include the task message, NOT all messages from state
    # The reporter doesn't need the full conversation history - only the task and observations
    input_ = {
        "messages": [
            HumanMessage(
                f"# Research Requirements\n\n## Task\n\n{plan_title}\n\n## Description\n\n{plan_thought}"
            )
        ],
        "locale": state.get("locale", "en-US"),
    }
    # Get system prompt only (first message from apply_prompt_template)
    # Don't include all messages from state - that causes token overflow!
    all_template_messages = apply_prompt_template("reporter", input_, configurable, input_.get("locale", "en-US"))
    # Only take the system prompt (first message), not the rest
    invoke_messages = [all_template_messages[0]] if all_template_messages else []
    observations = state.get("observations", [])
    
    # CRITICAL: PRIORITIZE step execution results over ReAct intermediate steps
    # Step execution results contain the actual data from the planner flow
    # ReAct intermediate steps are only used as fallback if no plan steps exist
    step_observations = []
    has_completed_steps = False
    
    if current_plan and not isinstance(current_plan, str) and hasattr(current_plan, 'steps') and current_plan.steps:
        # Get token limit for reporter's model to adjust compression
        reporter_llm_type = AGENT_LLM_MAP.get("reporter", "basic")
        token_limit = get_llm_token_limit_by_type(reporter_llm_type)
        
        # Calculate compression limits based on model's token limit
        # Reserve 40% for prompt overhead (system messages, instructions, etc.)
        # Use remaining 60% for observations
        if token_limit:
            chars_per_token = 4
            reserved_tokens = int(token_limit * 0.4)  # Reserve 40% for prompt
            available_tokens = token_limit - reserved_tokens
            available_chars = available_tokens * chars_per_token
            
            # Distribute available chars across steps
            num_steps = len([s for s in current_plan.steps if s.execution_res])
            if num_steps > 0:
                max_length_per_step = min(available_chars // max(num_steps, 1), 30000)
                # Adjust max_items based on token limit
                if token_limit >= 100000:
                    max_items = 20
                elif token_limit >= 32000:
                    max_items = 15
                else:
                    max_items = 10
            else:
                max_length_per_step = 10000
                max_items = 10
        else:
            # Fallback to conservative defaults
            max_length_per_step = 10000
            max_items = 10
        
        logger.debug(f"[reporter_node] Token limit: {token_limit}, max_length_per_step: {max_length_per_step}, max_items: {max_items}")
        
        for idx, step in enumerate(current_plan.steps):
            if step.execution_res:
                execution_res = step.execution_res
                
                # Compress execution result if it's too large
                if len(str(execution_res)) > max_length_per_step:
                    try:
                        # Try to compress JSON arrays in the result
                        parsed = json.loads(str(execution_res))
                        from src.utils.json_utils import _compress_large_array
                        compressed = _compress_large_array(parsed, max_items=max_items)
                        execution_res = json.dumps(compressed, ensure_ascii=False)
                        logger.info(f"[reporter_node] Compressed step {idx + 1} ('{step.title}') from {len(str(step.execution_res))} to {len(execution_res)} chars")
                    except (json.JSONDecodeError, TypeError):
                        # Not JSON, just truncate
                        execution_res = str(execution_res)[:max_length_per_step] + f"\n\n... (truncated, original length: {len(str(step.execution_res))} chars) ..."
                        logger.warning(f"[reporter_node] Truncated step {idx + 1} ('{step.title}') from {len(str(step.execution_res))} to {len(execution_res)} chars")
                
                # Include step title for context
                step_obs = f"## Step {idx + 1}: {step.title}\n\n{execution_res}"
                step_observations.append(step_obs)
                has_completed_steps = True
                logger.info(f"Reporter: Collected observation from step {idx + 1}: {step.title} ({len(str(execution_res))} chars)")
        
        # Use step observations if we have completed steps (PRIORITY)
        if step_observations and has_completed_steps:
            logger.info(f"Reporter: Using step execution results ({len(step_observations)} steps) - PRIORITY over state observations")
            observations = step_observations
        elif step_observations:
            # Merge step observations with state observations if no completed steps
            if len(step_observations) > len(observations):
                logger.info(f"Reporter: Using step observations ({len(step_observations)}) instead of state observations ({len(observations)})")
                observations = step_observations
            else:
                # Merge both sources, avoiding duplicates
                all_observations = list(observations)
                for step_obs in step_observations:
                    if step_obs not in all_observations:
                        all_observations.append(step_obs)
                observations = all_observations
    
    # FALLBACK: Extract observations from ReAct agent's intermediate steps ONLY if no step observations
    # ReAct agent stores tool calls/results in react_intermediate_steps, not observations
    if not observations or not has_completed_steps:
        react_intermediate_steps = state.get("react_intermediate_steps", [])
        if react_intermediate_steps:
            logger.info(f"Reporter: No step observations found, extracting from ReAct intermediate steps ({len(react_intermediate_steps)} steps)")
            react_observations = []
            for step_idx, step in enumerate(react_intermediate_steps):
                logger.debug(f"Reporter: Processing ReAct step {step_idx + 1}: type={type(step)}")
                if isinstance(step, (list, tuple)) and len(step) >= 2:
                    action = step[0]  # Tool call (AgentAction object)
                    observation = step[1]  # Tool result
                    
                    # Extract tool name and input from AgentAction
                    tool_name = getattr(action, 'tool', None) or (action.tool if hasattr(action, 'tool') else str(action))
                    tool_input = getattr(action, 'tool_input', None) or (action.tool_input if hasattr(action, 'tool_input') else {})
                    
                    # Format as observation string
                    obs_text = f"Tool: {tool_name}\nInput: {tool_input}\nResult: {observation}"
                    react_observations.append(obs_text)
                    logger.info(f"Reporter: Extracted observation {step_idx + 1}: {tool_name} -> {len(str(observation))} chars")
                else:
                    logger.warning(f"Reporter: ReAct step {step_idx + 1} has unexpected structure: {type(step)}")
            
            if react_observations:
                observations = react_observations
                logger.info(f"Reporter: Extracted {len(observations)} observations from ReAct steps (FALLBACK)")
            else:
                logger.warning("Reporter: Failed to extract observations from ReAct intermediate steps")

    # CRITICAL: Detect if this is a simple query (list/show/get) that doesn't need comprehensive analysis
    # Simple queries should just present the data directly, not generate comprehensive project analysis
    is_simple_query = False
    if is_from_react:
        # Check if the query is a simple list/show/get query
        query_lower = plan_title.lower()
        simple_keywords = [
            "list users", "show users", "list all users", "show all users",
            "list projects", "show projects", "list all projects",
            "list sprints", "show sprints", "list all sprints",
            "list tasks", "show tasks", "list all tasks",
            "list epics", "show epics", "list all epics",
            "get user", "get project", "get sprint", "get task", "get epic",
            "current user", "who am i", "show me all users", "show me users"
        ]
        is_simple_query = any(keyword in query_lower for keyword in simple_keywords)
        if is_simple_query:
            logger.info(f"[REPORTER] 🎯 Simple query detected - will format as simple list/table, not comprehensive analysis")
    
    # Add a reminder about the new report format, citation style, and table usage
    format_instructions = "IMPORTANT: Structure your report according to the format in the prompt. Remember to include:\n\n1. Key Points - A bulleted list of the most important findings\n2. Overview - A brief introduction to the topic\n3. Detailed Analysis - Organized into logical sections\n4. Survey Note (optional) - For more comprehensive reports\n5. Key Citations - List all references at the end\n\nFor citations, DO NOT include inline citations in the text. Instead, place all citations in the 'Key Citations' section at the end using the format: `- [Source Title](URL)`. Include an empty line between each citation for better readability.\n\nPRIORITIZE USING MARKDOWN TABLES for data presentation and comparison. Use tables whenever presenting comparative data, statistics, features, or options. Structure tables with clear headers and aligned columns. Example table format:\n\n| Feature | Description | Pros | Cons |\n|---------|-------------|------|------|\n| Feature 1 | Description 1 | Pros 1 | Cons 1 |\n| Feature 2 | Description 2 | Pros 2 | Cons 2 |"
    
    # For simple queries, add special instruction to NOT generate comprehensive analysis
    if is_simple_query:
        format_instructions += "\n\n🔴 CRITICAL FOR SIMPLE QUERIES: This is a simple list/show/get query. DO NOT generate a comprehensive project analysis report with all 10 analytics sections (Executive Summary, Sprint Overview, Burndown Chart, Velocity Chart, CFD, Cycle Time, Work Distribution, Issue Trend, Task Statistics, Key Insights). Instead, simply present the requested data in a clear, organized format (preferably using tables). For example, if the user asked to 'list users', just show the users in a table with their details. Keep it simple and direct - no need for comprehensive analytics sections."
    
    invoke_messages.append(
        HumanMessage(
            content=format_instructions,
            name="system",
        )
    )

    observation_messages = []
    for observation in observations:
        observation_messages.append(
            HumanMessage(
                content=f"Below are some observations for the research task:\n\n{observation}",
                name="observation",
            )
        )

    # Log observations for debugging (especially for PM data queries)
    logger.info(f"Reporter: Received {len(observations)} observations (from state and/or completed steps)")
    for idx, obs in enumerate(observations):
        obs_preview = str(obs)[:200] if len(str(obs)) > 200 else str(obs)
        logger.debug(f"Observation {idx + 1}: {obs_preview}")

    # 🔴 VALIDATION: Check if observations contain real data (not just errors)
    has_real_data = False
    
    for obs in observations:
        obs_str = str(obs)
        # Check if observation contains actual data (not just errors)
        if obs_str and len(obs_str) > 50:  # Minimum length to be meaningful
            # Check if it's not just an error message
            if not (obs_str.startswith("[ERROR]") or 
                    "Error" in obs_str[:100] or 
                    "error" in obs_str[:100].lower() or
                    "failed" in obs_str[:100].lower() or
                    "rate limit" in obs_str.lower() or
                    "token limit" in obs_str.lower()):
                has_real_data = True
                break
            # If it's an error but also has some data, that's still useful
            if len(obs_str) > 200 and not obs_str.startswith("[ERROR]"):
                has_real_data = True
    
    # If no real data is available, add a warning to the reporter
    if not has_real_data and len(observations) > 0:
        logger.warning(
            f"Reporter: No real data found in {len(observations)} observations. "
            "All observations appear to be errors or empty. Adding warning to reporter."
        )
        invoke_messages.append(
            HumanMessage(
                content=(
                    "🔴 CRITICAL WARNING: The observations provided contain only errors or are empty. "
                    "You MUST NOT generate fake data. Instead, you MUST report that:\n"
                    "1. The data collection failed\n"
                    "2. No real data is available\n"
                    "3. The report cannot be generated without actual data\n\n"
                    "DO NOT create fake metrics, tables, statistics, or any data. "
                    "State clearly that data is unavailable."
                ),
                name="system",
            )
        )
    elif len(observations) == 0:
        logger.warning("Reporter: No observations provided at all. Adding warning to reporter.")
        invoke_messages.append(
            HumanMessage(
                content=(
                    "🔴 CRITICAL WARNING: No observations were provided. "
                    "You MUST report that no data was collected and the report cannot be generated. "
                    "DO NOT create fake data."
                ),
                name="system",
            )
        )

    # Context compression WITH token budget coordination
    # Account for frontend conversation history + system prompts + overhead
    llm_token_limit = get_llm_token_limit_by_type(AGENT_LLM_MAP["reporter"])
    if llm_token_limit is None:
        logger.warning("[reporter_node] Token limit unknown, using default 16385")
        llm_token_limit = 16385  # Default for gpt-3.5-turbo
    
    # Get the actual model name for accurate token counting
    reporter_llm = get_llm_by_type(AGENT_LLM_MAP["reporter"])
    model_name = getattr(reporter_llm, "model_name", None) or getattr(reporter_llm, "model", None) or "gpt-3.5-turbo"
    
    # CRITICAL: Use ADAPTIVE token budget based on model's context window
    # Extract frontend messages for budgeting
    frontend_count = state.get("frontend_history_message_count", 0)
    all_messages = list(state.get("messages", []))
    frontend_messages = all_messages[:frontend_count] if frontend_count > 0 else []
    
    # Get adaptive context manager (uses percentage of model's context)
    from src.utils.adaptive_context_config import get_adaptive_context_manager
    context_manager = get_adaptive_context_manager(
        agent_type="reporter",
        model_name=model_name,
        model_context_limit=llm_token_limit,
        frontend_history_messages=frontend_messages
    )
    
    logger.info(
        f"[reporter_node] Token budget: total={llm_token_limit}, "
        f"frontend_history={frontend_count} messages, "
        f"adjusted_limit={context_manager.token_limit}"
    )
    
    # CRITICAL: Compress ALL messages (system prompt + task + observations) together
    # This ensures context optimization is applied to everything, not just observations
    all_messages_to_compress = invoke_messages + observation_messages
    
    # DEBUG: Log what we're compressing
    logger.info(
        f"Reporter: Compressing {len(invoke_messages)} invoke messages + {len(observation_messages)} observation messages = {len(all_messages_to_compress)} total"
    )
    
    # Count original tokens for logging
    original_token_count = context_manager.count_tokens(all_messages_to_compress, model=model_name)
    logger.info(
        f"Reporter: Original token count: {original_token_count:,} tokens "
        f"(invoke: {len(invoke_messages)} msgs, observations: {len(observation_messages)} msgs)"
    )
    
    # Compress all messages together to fit in token budget
    compressed_state = context_manager.compress_messages(
        {"messages": all_messages_to_compress}
    )
    optimization_messages = []
    if isinstance(compressed_state, dict):
        compressed_messages = compressed_state.get("messages", [])
        optimization_metadata = compressed_state.get("_context_optimization")
        
        # Create context optimization tool call messages
        if optimization_metadata:
            optimization_messages = _add_context_optimization_tool_call(state, "reporter", optimization_metadata)
    else:
        compressed_messages = all_messages_to_compress
    
    # Log compression results for debugging
    compressed_token_count = context_manager.count_tokens(compressed_messages, model=model_name)
    if compressed_token_count < original_token_count:
        reduction_pct = ((original_token_count - compressed_token_count) / original_token_count) * 100
        logger.info(
            f"Reporter: All messages compressed from {original_token_count} to {compressed_token_count} tokens "
            f"({reduction_pct:.1f}% reduction)"
        )
    
    # Use compressed messages (includes system prompt + task + observations)
    invoke_messages = compressed_messages

    # CRITICAL: Add optimization messages to invoke_messages BEFORE counting tokens
    # This ensures we count the actual messages that will be sent to the LLM
    if optimization_messages:
        invoke_messages = optimization_messages + invoke_messages

    # Final check: if still over limit, truncate aggressively
    total_tokens = context_manager.count_tokens(invoke_messages, model=model_name)
    logger.info(
        f"Reporter: Token count check - total_tokens={total_tokens:,}, limit={llm_token_limit:,}, "
        f"compressed_token_count={compressed_token_count:,}, optimization_msgs={len(optimization_messages)}"
    )
    
    if total_tokens > llm_token_limit:
        logger.warning(
            f"Reporter: Total tokens ({total_tokens:,}) still exceed limit ({llm_token_limit:,}). "
            f"Applying aggressive truncation."
        )
        # Calculate how much we need to reduce
        # Reserve space for optimization messages and system prompt overhead
        optimization_tokens = context_manager.count_tokens(optimization_messages, model=model_name) if optimization_messages else 0
        system_overhead = 1000  # Reserve for system prompt and overhead
        available_for_data = llm_token_limit - optimization_tokens - system_overhead
        excess_tokens = total_tokens - llm_token_limit
        target_data_tokens = max(1000, available_for_data - 500)  # Leave 500 token buffer
        
        logger.info(
            f"Reporter: Truncation plan - optimization_tokens={optimization_tokens}, "
            f"available_for_data={available_for_data:,}, target_data_tokens={target_data_tokens:,}"
        )
        
        # Truncate each message in compressed_messages proportionally
        # CRITICAL: Always truncate if we're over limit, regardless of compressed_token_count
        # The compressed_token_count might be from before optimization messages were added
        if compressed_messages and total_tokens > llm_token_limit:
            # Calculate target tokens per message
            target_per_msg = target_data_tokens // max(1, len(compressed_messages))
            truncated_messages = []
            current_total = 0
            
            for i, msg in enumerate(compressed_messages):
                # Count tokens - use accurate counting for both dict and message objects
                # Convert dict to message object temporarily for accurate counting, or use count_tokens directly
                if isinstance(msg, dict):
                    # For dict messages, use count_tokens which handles dicts correctly
                    msg_tokens = context_manager.count_tokens([msg], model=model_name)
                else:
                    msg_tokens = context_manager._count_message_tokens(msg)
                
                remaining_budget = target_data_tokens - current_total
                remaining_msgs = len(compressed_messages) - i
                # Distribute remaining budget among remaining messages
                if remaining_msgs > 0:
                    max_for_this_msg = remaining_budget // remaining_msgs
                else:
                    max_for_this_msg = remaining_budget
                
                # CRITICAL: Always truncate if message is too large, even if max_for_this_msg is small
                # Convert tokens to approximate characters (4 chars per token)
                max_chars = max_for_this_msg * 4
                truncated_msg = copy.deepcopy(msg)
                original_content_len = 0
                truncated = False
                
                # Handle both dict messages and message objects
                if isinstance(truncated_msg, dict):
                    content = truncated_msg.get("content", "")
                    if isinstance(content, str):
                        original_content_len = len(content)
                        # Truncate if content is longer than max_chars (always truncate if over budget)
                        if len(content) > max_chars:
                            truncated_msg["content"] = content[:max_chars] + "\n\n... (truncated due to context length limit) ..."
                            truncated = True
                            logger.info(f"Reporter: Truncated dict message {i} from {original_content_len} to {max_chars} chars (target: {max_for_this_msg} tokens)")
                elif hasattr(truncated_msg, 'content') and isinstance(truncated_msg.content, str):
                    original_content_len = len(truncated_msg.content)
                    if len(truncated_msg.content) > max_chars:
                        truncated_msg.content = truncated_msg.content[:max_chars] + "\n\n... (truncated due to context length limit) ..."
                        truncated = True
                        logger.info(f"Reporter: Truncated message object {i} from {original_content_len} to {max_chars} chars (target: {max_for_this_msg} tokens)")
                
                truncated_messages.append(truncated_msg)
                # Count tokens after truncation - use accurate counting
                if isinstance(truncated_msg, dict):
                    # Use count_tokens which handles dicts correctly
                    new_msg_tokens = context_manager.count_tokens([truncated_msg], model=model_name)
                else:
                    new_msg_tokens = context_manager._count_message_tokens(truncated_msg)
                current_total += new_msg_tokens
                if truncated:
                    logger.info(f"Reporter: Message {i} tokens: {msg_tokens} → {new_msg_tokens} (target: {max_for_this_msg})")
            
            compressed_messages = truncated_messages
            # Rebuild invoke_messages with truncated compressed_messages
            if optimization_messages:
                invoke_messages = optimization_messages + compressed_messages
            else:
                invoke_messages = compressed_messages
            
            # CRITICAL: Recalculate token count after truncation
            final_tokens = context_manager.count_tokens(invoke_messages, model=model_name)
            logger.info(
                f"Reporter: After aggressive truncation - compressed_messages: {len(compressed_messages)}, "
                f"invoke_messages: {len(invoke_messages)}, total tokens: {final_tokens:,} (target: {llm_token_limit:,})"
            )
            
            # If still over limit, apply even more aggressive truncation
            if final_tokens > llm_token_limit:
                logger.warning(
                    f"Reporter: Still over limit after truncation ({final_tokens:,} > {llm_token_limit:,}). "
                    f"Applying emergency truncation."
                )
                # Emergency: truncate to 80% of limit
                emergency_target = int(llm_token_limit * 0.8)
                emergency_data_target = emergency_target - optimization_tokens - system_overhead
                
                # Truncate each message to fit emergency target
                emergency_messages = []
                max_chars_per_msg = (emergency_data_target * 4) // max(1, len(compressed_messages))
                logger.info(f"Reporter: Emergency truncation - max_chars_per_msg={max_chars_per_msg}, emergency_data_target={emergency_data_target}")
                
                for i, msg in enumerate(compressed_messages):
                    emergency_msg = copy.deepcopy(msg)
                    original_len = 0
                    
                    # Handle both dict messages and message objects
                    if isinstance(emergency_msg, dict):
                        content = emergency_msg.get("content", "")
                        if isinstance(content, str):
                            original_len = len(content)
                            if len(content) > max_chars_per_msg:
                                emergency_msg["content"] = content[:max_chars_per_msg] + "\n\n... (emergency truncation) ..."
                                logger.info(f"Reporter: Emergency truncated dict message {i} from {original_len} to {max_chars_per_msg} chars")
                    elif hasattr(emergency_msg, 'content') and isinstance(emergency_msg.content, str):
                        original_len = len(emergency_msg.content)
                        if len(emergency_msg.content) > max_chars_per_msg:
                            emergency_msg.content = emergency_msg.content[:max_chars_per_msg] + "\n\n... (emergency truncation) ..."
                            logger.info(f"Reporter: Emergency truncated message object {i} from {original_len} to {max_chars_per_msg} chars")
                    
                    emergency_messages.append(emergency_msg)
                
                compressed_messages = emergency_messages
                if optimization_messages:
                    invoke_messages = optimization_messages + compressed_messages
                else:
                    invoke_messages = compressed_messages
                
                final_tokens = context_manager.count_tokens(invoke_messages, model=model_name)
                logger.info(
                    f"Reporter: After emergency truncation, total tokens: {final_tokens:,} (target: {llm_token_limit:,})"
                )
                
                # If STILL over limit, return error
                if final_tokens > llm_token_limit:
                    logger.error(
                        f"Reporter: Still over limit after emergency truncation ({final_tokens:,} > {llm_token_limit:,}). "
                        f"Will return error message instead."
                    )
                    # This will be caught by the try/except below and return an error

    # Use accurate token counting with tiktoken
    accurate_token_count = context_manager.count_tokens(invoke_messages, model=model_name)
    logger.info(
        f"Reporter: Accurate token count: {accurate_token_count} (limit: {llm_token_limit})"
    )
    
    # If accurate count suggests we're over, apply more aggressive compression
    if accurate_token_count > llm_token_limit * 0.8:  # If over 80% of limit, be aggressive
        logger.warning(
            f"Reporter: Accurate token count ({accurate_token_count}) exceeds 80% of limit ({llm_token_limit}). "
            f"Applying aggressive compression."
        )
        # Calculate target size more aggressively - reserve 40% for system and overhead
        available_for_data = int(llm_token_limit * 0.6)  # Use only 60% for data
        target_chars = int(available_for_data * 2.5)  # Convert to chars (conservative), ensure int
        if compressed_messages:
            target_per_msg = int(target_chars // max(1, len(compressed_messages)))  # Ensure int
            more_aggressive_messages = []
            for msg in compressed_messages:
                # Handle both dict messages (from apply_prompt_template) and message objects
                if isinstance(msg, dict):
                    content = msg.get("content", "")
                    if isinstance(content, str) and len(content) > target_per_msg:
                        truncated_msg = msg.copy()
                        truncated_msg["content"] = content[:int(target_per_msg)] + "\n\n... (data truncated due to context limits) ..."
                        more_aggressive_messages.append(truncated_msg)
                        logger.debug(f"Reporter: Truncated dict message from {len(content)} to {target_per_msg} chars")
                    else:
                        more_aggressive_messages.append(msg)
                elif hasattr(msg, 'content') and isinstance(msg.content, str):
                    msg_chars = len(msg.content)
                    if msg_chars > target_per_msg:
                        truncated_msg = copy.deepcopy(msg)
                        # Truncate more aggressively - ensure target_per_msg is int
                        truncated_msg.content = msg.content[:int(target_per_msg)] + "\n\n... (data truncated due to context limits) ..."
                        more_aggressive_messages.append(truncated_msg)
                        logger.debug(f"Reporter: Truncated message from {msg_chars} to {target_per_msg} chars")
                    else:
                        more_aggressive_messages.append(msg)
                else:
                    more_aggressive_messages.append(msg)
            compressed_messages = more_aggressive_messages
            invoke_messages = invoke_messages[:len(invoke_messages) - len(compressed_messages)] + compressed_messages
            logger.info(f"Reporter: Applied aggressive character-based truncation (target: {target_chars} total, {target_per_msg} per message)")
    
    # Final check with accurate token count
    final_total_tokens = context_manager.count_tokens(invoke_messages, model=model_name)
    logger.info(
        f"Reporter: After compression - Accurate token count: {final_total_tokens} (limit: {llm_token_limit})"
    )
    
    # If still over limit, STOP and return error immediately (don't call LLM)
    if final_total_tokens > llm_token_limit * 0.95:  # 95% threshold - use accurate count
        logger.error(
            f"Reporter: Final token count ({final_total_tokens}) exceeds 95% of limit ({llm_token_limit}). "
            f"Cannot generate report - context too large even after compression."
        )
        
        # Create user-friendly error message
        error_message = (
            f"❌ **Context Too Large**\n\n"
            f"The analysis data ({final_total_tokens:,} tokens) exceeds the model's limit ({llm_token_limit:,} tokens).\n\n"
            f"**Current model:** {model_name} (max {llm_token_limit:,} tokens)\n\n"
            f"**Solutions:**\n"
            f"1. ✅ **Switch to a larger model:**\n"
            f"   - GPT-4o (128,000 tokens)\n"
            f"   - Claude 3.5 Sonnet (200,000 tokens)\n"
            f"   - DeepSeek (64,000 tokens)\n\n"
            f"2. Request a more focused analysis with fewer steps\n\n"
            f"3. Reduce the number of sprints or tasks being analyzed"
        )
        
        # Return error message to user (don't crash the workflow)
        error_ai_message = AIMessage(
            content=error_message,
            name="reporter",
            response_metadata={"finish_reason": "stop", "error_type": "context_too_large"}
        )
        
        return {
            "messages": [error_ai_message],
            "final_report": error_message,
        }
    
    # Debug: Log what we're actually sending to the LLM
    logger.info(f"Reporter: About to invoke LLM with {len(invoke_messages)} messages")
    for idx, msg in enumerate(invoke_messages):
        if isinstance(msg, dict):
            msg_type = f"dict(role={msg.get('role', 'unknown')})"
            content_len = len(str(msg.get('content', '')))
        else:
            msg_type = type(msg).__name__
            content_len = len(str(getattr(msg, 'content', '')))
        logger.info(f"  Message {idx}: {msg_type}, content_len={content_len}")
    
    # Wrap LLM invocation in try/except to catch errors and notify user/LLM
    try:
        response = get_llm_by_type(AGENT_LLM_MAP["reporter"]).invoke(invoke_messages)
        response_content = response.content
        logger.info(f"reporter response: {response_content}")

        # Use the response directly instead of creating a new AIMessage
        # This prevents duplicate messages - LangGraph already streams the LLM response
        # We just need to set the name and ensure finish_reason is set
        if not hasattr(response, 'name') or not response.name:
            response.name = "reporter"
        if not response.response_metadata:
            response.response_metadata = {}
        if "finish_reason" not in response.response_metadata:
            response.response_metadata["finish_reason"] = "stop"

        # Add AIMessage so the final report gets streamed to the client
        # Use the original response object to maintain the same ID
        # Include optimization messages if they exist
        return_messages = [response]
        if optimization_messages:
            return_messages = optimization_messages + return_messages
        
        return {
            "messages": return_messages,
            "final_report": response_content,
        }
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        error_message = f"Error in reporter node: {str(e)}"
        logger.error(f"[reporter_node] {error_message}", exc_info=True)
        logger.error(f"Full traceback:\n{error_traceback}")
        
        # Check for context length errors specifically
        error_str = str(e)
        is_context_length_error = (
            "context_length_exceeded" in error_str.lower() or
            "maximum context length" in error_str.lower() or
            "context length" in error_str.lower() and "exceeded" in error_str.lower()
        )
        
        if is_context_length_error:
            # Extract token information if available
            token_info = ""
            if "tokens" in error_str:
                token_match = re.search(r'(\d+)\s*tokens', error_str)
                if token_match:
                    actual_tokens = token_match.group(1)
                    token_info = f" (actual: {actual_tokens} tokens)"
            
            detailed_error = f"""[ERROR] Reporter Failed: Context Length Exceeded

The report generation failed because the data is too large for the current model's context window{token_info}.

**What happened:**
- All research steps completed successfully
- The reporter attempted to generate the final report
- The combined data exceeded the model's token limit

**Possible solutions:**
1. Use a model with a larger context window (e.g., GPT-4o, Claude 3.5)
2. Reduce the amount of data in the analysis
3. Request a more focused analysis with fewer steps

**Error Details:** {error_str[:500]}"""
        else:
            detailed_error = f"""[ERROR] Reporter Failed

The report generation encountered an error.

**Error Details:** {error_str[:500]}

**What to do:**
- Check the server logs for more details
- Try the analysis again
- If the error persists, contact support"""
        
        # Add error to the current plan's last step so user sees it in the step list
        # This ensures the user knows which step failed
        error_observation = detailed_error
        
        # Update the last step's execution_res to include the error
        # This makes the error visible in the frontend step list
        if current_plan and not isinstance(current_plan, str) and hasattr(current_plan, 'steps') and current_plan.steps:
            from src.prompts.planner_model import Step
            
            # Find the last step and update it with error
            last_step_idx = len(current_plan.steps) - 1
            last_step = current_plan.steps[last_step_idx]
            
            # Create updated step with error appended to execution_res
            updated_last_step = Step(
                need_search=last_step.need_search,
                title=last_step.title,
                description=last_step.description,
                step_type=last_step.step_type,
                execution_res=f"{last_step.execution_res or ''}\n\n{detailed_error}" if last_step.execution_res else detailed_error,
            )
            
            # Create updated plan with error step
            updated_steps = list(current_plan.steps)
            updated_steps[last_step_idx] = updated_last_step
            updated_plan = Plan(
                locale=current_plan.locale,
                has_enough_context=current_plan.has_enough_context,
                thought=current_plan.thought,
                title=current_plan.title,
                steps=updated_steps,
            )
        else:
            updated_plan = current_plan
        
        # Create an error message for the user
        # Use AIMessage with finish_reason="stop" so frontend recognizes completion
        error_ai_message = AIMessage(
            content=detailed_error,
            name="reporter",
            response_metadata={"finish_reason": "stop", "error_type": type(e).__name__}
        )
        
        # Return error state so it gets streamed to frontend
        # DON'T return current_plan here - validator will handle plan updates
        # This prevents LangGraph state conflicts (multiple writers to current_plan)
        return {
            "messages": [error_ai_message],
            "observations": observations + [error_observation],
            "final_report": detailed_error,  # Store error as final report so user sees it
            # Note: current_plan omitted - validator will update it for retry logic
        }


def research_team_node(state: State):  # noqa: ARG001
    logger.info(f"[DEBUG-NODES] [NODE-RESEARCH-TEAM-1] Research team node entered")
    """Research team node that routes to appropriate agent or reporter.
    
    NOTE: This node does NOT return a Command for routing. The routing is handled
    by the conditional edge function continue_to_running_research_team() in builder.py.
    This prevents conflicts between Command.goto and conditional edge routing.
    """
    logger.info("Research team node - checking step completion status")
    
    # Check if all steps are complete (for logging only)
    current_plan = state.get("current_plan")
    if current_plan and not isinstance(current_plan, str) and current_plan.steps:
        all_complete = all(step.execution_res for step in current_plan.steps)
        if all_complete:
            logger.info(f"[research_team_node] All {len(current_plan.steps)} steps completed! Conditional edge will route to validator.")
    
    logger.debug("Entering research_team_node - coordinating research and coder agents")


async def _execute_agent_step(
    state: State, agent, agent_name: str
) -> Command[Literal["research_team"]]:
    """Helper function to execute a step using the specified agent."""
    import sys
    logger.info(f"[DEBUG-NODES] [EXEC-1] [{agent_name}] _execute_agent_step entered")
    sys.stderr.write(f"\n⚡ EXECUTE_AGENT_STEP: agent_name='{agent_name}'\n")
    sys.stderr.flush()
    
    logger.debug(f"[_execute_agent_step] Starting execution for agent: {agent_name}")
    
    current_plan = state.get("current_plan")
    if not current_plan or isinstance(current_plan, str):
        logger.error("[_execute_agent_step] Invalid or missing current_plan")
        return Command(goto="research_team")
    
    plan_title = current_plan.title
    observations = state.get("observations", [])
    
    sys.stderr.write(f"\n📋 PLAN INFO: plan_title='{plan_title}'\n")
    sys.stderr.flush()
    
    logger.debug(f"[_execute_agent_step] Plan title: {plan_title}, observations count: {len(observations)}")

    # Find the first unexecuted step
    current_step = None
    current_step_idx = None
    completed_steps = []
    if not hasattr(current_plan, 'steps') or not current_plan.steps:
        logger.error("[_execute_agent_step] Plan has no steps")
        return Command(goto="research_team")
    
    for idx, step in enumerate(current_plan.steps):
        if not step.execution_res:
            current_step = step
            current_step_idx = idx  # Store the index for later use
            logger.debug(f"[_execute_agent_step] Found unexecuted step at index {idx}: {step.title}")
            break
        else:
            completed_steps.append(step)

    if not current_step:
        # All steps are complete - route to reporter
        logger.info(f"[_execute_agent_step] All {len(current_plan.steps)} steps completed! Routing to reporter.")
        return Command(goto="reporter")

    logger.info(f"[_execute_agent_step] Executing step: {current_step.title}, agent: {agent_name}")
    logger.debug(f"[_execute_agent_step] Completed steps so far: {len(completed_steps)}")
    step_start_time = time.time()
    logger.info(f"[STEP-TIMING] Starting step '{current_step.title}' at {step_start_time}")

    # Get token limit for this agent's model to adjust compression dynamically
    agent_llm_type = AGENT_LLM_MAP.get(agent_name, "basic")
    token_limit = get_llm_token_limit_by_type(agent_llm_type)
    
    # Calculate compression limits based on model's token limit
    # Reserve 40% for prompt overhead (system messages, current step, tools, etc.)
    # Use remaining 60% for completed steps data (more conservative to account for function tokens)
    if token_limit:
        # Estimate: ~4 characters per token (conservative estimate)
        chars_per_token = 4
        reserved_tokens = int(token_limit * 0.4)  # Reserve 40% for prompt, tools, and overhead
        available_tokens = token_limit - reserved_tokens
        available_chars = available_tokens * chars_per_token
        
        # Distribute available chars across completed steps (with aggressive limits)
        num_completed_steps = len(completed_steps)
        if num_completed_steps > 0:
            # Allocate chars per step, but cap aggressively to prevent overflow
            # For PM agent with many steps, be very conservative
            chars_per_step = available_chars // max(num_completed_steps, 1)
            # Cap at 10K chars per step (2.5K tokens) to prevent any single step from being too large
            max_length_per_step = min(chars_per_step, 10000)
            # Adjust max_items based on token limit and number of steps (fewer items when more steps)
            if token_limit >= 100000:  # Large context models (Claude, GPT-4o, Gemini)
                max_items = max(5, 20 - num_completed_steps)  # Reduce items as steps increase
            elif token_limit >= 32000:  # Medium context models
                max_items = max(5, 15 - num_completed_steps // 2)
            else:  # Small context models (GPT-3.5-turbo)
                max_items = max(3, 10 - num_completed_steps // 2)  # Very conservative for small models
        else:
            max_length_per_step = 10000  # Default if no completed steps
            max_items = 10
    else:
        # Fallback to conservative defaults if token limit unknown
        logger.warning(f"[_execute_agent_step] Token limit unknown for agent '{agent_name}', using conservative defaults")
        max_length_per_step = 5000  # More conservative default
        max_items = 5
    
    logger.info(f"[_execute_agent_step] Agent '{agent_name}' token_limit={token_limit}, completed_steps={len(completed_steps)}, max_length_per_step={max_length_per_step}, max_items={max_items}, available_chars={available_chars if token_limit else 'N/A'}")

    # Format completed steps information
    # CRITICAL: Compress ALL execution results to prevent token overflow
    # Even if individual results are small, the total can exceed limits
    # Note: sanitize_tool_response is already imported at module level
    from src.utils.json_utils import _compress_large_array
    
    completed_steps_info = ""
    if completed_steps:
        completed_steps_info = "# Completed Research Steps\n\n"
        total_chars_used = 0
        for i, step in enumerate(completed_steps):
            # ALWAYS compress execution results to ensure they fit within token budget
            execution_res = step.execution_res
            original_length = len(str(execution_res)) if execution_res else 0
            
            if execution_res:
                # Calculate remaining budget for this step
                remaining_budget = max_length_per_step - (len(completed_steps_info) - total_chars_used)
                step_max_length = min(max_length_per_step, remaining_budget)
                
                # Always apply compression/truncation to fit within budget
                try:
                    parsed = json.loads(str(execution_res))
                    # First compress arrays
                    compressed = _compress_large_array(parsed, max_items=max_items)
                    compressed_json = json.dumps(compressed, ensure_ascii=False)
                    # Then sanitize to ensure it fits within step_max_length (sanitize_tool_response imported at top)
                    execution_res = sanitize_tool_response(compressed_json, max_length=step_max_length, compress_arrays=False)
                    logger.info(f"[_execute_agent_step] Compressed execution result for step '{step.title}': {original_length:,} → {len(execution_res):,} chars (budget={step_max_length:,})")
                except (json.JSONDecodeError, TypeError):
                    # Not JSON, use sanitize_tool_response for truncation (already imported at top)
                    execution_res = sanitize_tool_response(str(execution_res), max_length=step_max_length, compress_arrays=False)
                    logger.info(f"[_execute_agent_step] Truncated non-JSON execution result for step '{step.title}': {original_length:,} → {len(execution_res):,} chars (budget={step_max_length:,})")
            
            step_info = f"## Completed Step {i + 1}: {step.title}\n\n<finding>\n{execution_res}\n</finding>\n\n"
            completed_steps_info += step_info
            total_chars_used += len(step_info)
        
        # Final check: if total exceeds available budget, truncate the entire string
        if len(completed_steps_info) > available_chars:
            logger.warning(f"[_execute_agent_step] Total completed_steps_info ({len(completed_steps_info):,} chars) exceeds budget ({available_chars:,} chars). Truncating...")
            completed_steps_info = completed_steps_info[:available_chars] + "\n\n... (truncated due to token limit) ..."

    # Prepare the input for the agent with completed steps info
    # Include project_id if available (for PM Agent)
    project_id = state.get("project_id", "")
    project_id_info = f"\n\n## Project ID\n\n{project_id}" if project_id else ""
    
    agent_input = {
        "messages": [
            HumanMessage(
                content=f"# Research Topic\n\n{plan_title}\n\n{completed_steps_info}# Current Step\n\n## Title\n\n{current_step.title}\n\n## Description\n\n{current_step.description}{project_id_info}\n\n## Locale\n\n{state.get('locale', 'en-US')}"
            )
        ]
    }

    # Add citation reminder for researcher agent
    if agent_name == "researcher":
        resources = state.get("resources")
        if resources:
            resources_info = "**The user mentioned the following resource files:**\n\n"
            for resource in resources:
                resources_info += f"- {resource.title} ({resource.description})\n"

            agent_input["messages"].append(
                HumanMessage(
                    content=resources_info
                    + "\n\n"
                    + "You MUST use the **local_search_tool** to retrieve the information from the resource files.",
                )
            )

        agent_input["messages"].append(
            HumanMessage(
                content="IMPORTANT: DO NOT include inline citations in the text. Instead, track all sources and include a References section at the end using link reference format. Include an empty line between each citation for better readability. Use this format for each reference:\n- [Source Title](URL)\n\n- [Another Source](URL)",
                name="system",
            )
        )

    # Invoke the agent
    sys.stderr.write(f"\n🎯 INVOKING AGENT: agent_name='{agent_name}', step='{current_step.title if current_step else 'N/A'}'\n")
    sys.stderr.flush()
    
    default_recursion_limit = 25
    try:
        env_value_str = os.getenv("AGENT_RECURSION_LIMIT", str(default_recursion_limit))
        parsed_limit = int(env_value_str)

        if parsed_limit > 0:
            recursion_limit = parsed_limit
            logger.info(f"Recursion limit set to: {recursion_limit}")
        else:
            logger.warning(
                f"AGENT_RECURSION_LIMIT value '{env_value_str}' (parsed as {parsed_limit}) is not positive. "
                f"Using default value {default_recursion_limit}."
            )
            recursion_limit = default_recursion_limit
    except ValueError:
        raw_env_value = os.getenv("AGENT_RECURSION_LIMIT")
        logger.warning(
            f"Invalid AGENT_RECURSION_LIMIT value: '{raw_env_value}'. "
            f"Using default value {default_recursion_limit}."
        )
        recursion_limit = default_recursion_limit

    sys.stderr.write(f"\n📥 AGENT INPUT: messages_count={len(agent_input.get('messages', []))}\n")
    if agent_input.get('messages'):
        first_msg = agent_input['messages'][0]
        msg_type = type(first_msg).__name__
        msg_content = str(first_msg.content) if hasattr(first_msg, 'content') else 'N/A'
        # Check if project_id is in content
        has_project_id = 'project_id' in msg_content.lower() or 'd7e300c6' in msg_content
        sys.stderr.write(f"📥 First message type: {msg_type}\n")
        sys.stderr.write(f"📥 Content length: {len(msg_content)}, has_project_id: {has_project_id}\n")
        sys.stderr.write(f"📥 Content preview: {msg_content[:800]}...\n")
    sys.stderr.flush()
    
    logger.info(f"Agent input: {agent_input}")
    logger.debug(
        f"[{agent_name}] Agent input details: "
        f"messages_count={len(agent_input.get('messages', []))}, "
        f"available_tools={[t.name if hasattr(t, 'name') else str(t) for t in agent_input.get('tools', [])]}"
    )
    
    # Validate message content before invoking agent
    try:
        from langchain_core.messages import BaseMessage
        validated_messages = validate_message_content(agent_input["messages"])
        agent_input["messages"] = list(validated_messages)  # Convert to list
    except Exception as validation_error:
        logger.error(f"Error validating agent input messages: {validation_error}")
    
    # CRITICAL: Apply context compression for PM agent to prevent context_length_exceeded errors
    # The agent input can be very large when there are many completed steps
    if agent_name == "pm_agent" and token_limit:
        logger.info(f"[{agent_name}] Applying context compression before agent invocation (token_limit={token_limit})")
        
        # Get model name for accurate token counting
        agent_llm_type = AGENT_LLM_MAP.get(agent_name, "basic")
        from src.llms.llm import get_llm_by_type
        agent_llm = get_llm_by_type(agent_llm_type)
        model_name = getattr(agent_llm, "model_name", None) or getattr(agent_llm, "model", None) or "gpt-3.5-turbo"
        
        # Create context manager for PM agent
        # Reserve 40% for system prompt, tools, and overhead, use 60% for messages
        from src.utils.adaptive_context_config import get_adaptive_context_manager
        context_manager = get_adaptive_context_manager(
            agent_type="pm_agent",
            model_name=model_name,
            model_context_limit=token_limit,
            frontend_history_messages=[]  # No frontend history for PM agent
        )
        
        # Count tokens in agent input messages
        input_token_count = context_manager.count_tokens(agent_input["messages"], model=model_name)
        logger.info(f"[{agent_name}] Agent input token count: {input_token_count:,} (limit: {token_limit:,})")
        
        # Account for function/tool definitions (typically 20-30% of context)
        # Reserve 30% for functions, system prompts, and overhead
        # Use 70% for actual messages
        message_token_limit = int(token_limit * 0.7)
        logger.info(f"[{agent_name}] Message token limit (70% of total): {message_token_limit:,} tokens")
        
        # If over message limit, compress/truncate the messages
        # Use a lower threshold (80% of message limit = 56% of total) to catch issues earlier
        if input_token_count > message_token_limit * 0.8:  # If over 80% of message limit, compress
            logger.warning(
                f"[{agent_name}] Agent input ({input_token_count:,} tokens) exceeds 80% of message limit ({message_token_limit:,}). "
                f"Compressing messages..."
            )
            
            # Compress messages using context manager
            compressed_state = context_manager.compress_messages({"messages": agent_input["messages"]})
            if isinstance(compressed_state, dict):
                compressed_messages = compressed_state.get("messages", [])
                if compressed_messages:
                    compressed_token_count = context_manager.count_tokens(compressed_messages, model=model_name)
                    logger.info(
                        f"[{agent_name}] Messages compressed: {input_token_count:,} → {compressed_token_count:,} tokens "
                        f"({((input_token_count - compressed_token_count) / input_token_count * 100):.1f}% reduction)"
                    )
                    agent_input["messages"] = compressed_messages
                    
                    # If still over limit after compression, apply aggressive truncation
                    if compressed_token_count > message_token_limit * 0.95:
                        logger.warning(
                            f"[{agent_name}] Still over limit after compression ({compressed_token_count:,} > {message_token_limit * 0.95:.0f}). "
                            f"Applying aggressive truncation..."
                        )
                        
                        # Truncate the first message (which contains completed_steps_info) more aggressively
                        if agent_input["messages"]:
                            first_msg = agent_input["messages"][0]
                            if hasattr(first_msg, 'content') and isinstance(first_msg.content, str):
                                # Calculate max chars for first message (reserve 10% for other messages)
                                max_chars_for_first = int((message_token_limit * 0.9) * 4)  # 90% of message tokens * 4 chars/token
                                if len(first_msg.content) > max_chars_for_first:
                                    original_len = len(first_msg.content)
                                    first_msg.content = first_msg.content[:max_chars_for_first] + "\n\n... (truncated due to context length limit) ..."
                                    logger.info(
                                        f"[{agent_name}] Aggressively truncated first message: {original_len:,} → {max_chars_for_first:,} chars"
                                    )
                                    
                                    # Recalculate token count
                                    final_token_count = context_manager.count_tokens(agent_input["messages"], model=model_name)
                                    logger.info(
                                        f"[{agent_name}] After aggressive truncation: {final_token_count:,} tokens (message limit: {message_token_limit:,}, total limit: {token_limit:,})"
                                    )
                                    
                                    # If STILL over message limit, return error instead of calling agent
                                    if final_token_count > message_token_limit:
                                        error_msg = (
                                            f"❌ **Context Too Large for {agent_name}**\n\n"
                                            f"The analysis data ({final_token_count:,} tokens) exceeds the model's limit ({token_limit:,} tokens).\n\n"
                                            f"**Current model:** {model_name} (max {token_limit:,} tokens)\n\n"
                                            f"**Solutions:**\n"
                                            f"1. Switch to a larger model (GPT-4o, Claude 3.5 Sonnet)\n"
                                            f"2. Request a more focused analysis with fewer steps\n"
                                            f"3. Reduce the amount of data being analyzed"
                                        )
                                        logger.error(f"[{agent_name}] Cannot proceed - context still too large after truncation")
                                        # Return error as execution result
                                        from src.prompts.planner_model import Step, Plan
                                        updated_step = Step(
                                            need_search=current_step.need_search,
                                            title=current_step.title,
                                            description=current_step.description,
                                            step_type=current_step.step_type,
                                            execution_res=error_msg,
                                        )
                                        updated_steps = list(current_plan.steps)
                                        updated_steps[current_step_idx] = updated_step
                                        updated_plan = Plan(
                                            locale=current_plan.locale,
                                            has_enough_context=current_plan.has_enough_context,
                                            thought=current_plan.thought,
                                            title=current_plan.title,
                                            steps=updated_steps,
                                        )
                                        completed_count = sum(1 for step in updated_plan.steps if step.execution_res)
                                        return Command(
                                            update={
                                                "messages": [HumanMessage(content=error_msg, name=agent_name)],
                                                "observations": observations + [error_msg],
                                                "current_plan": updated_plan,
                                                "current_step_index": min(completed_count, len(updated_plan.steps) - 1),
                                            },
                                            goto="research_team",
                                        )
        else:
            logger.info(f"[{agent_name}] Agent input within limit ({input_token_count:,} < {message_token_limit * 0.8:.0f}), no compression needed")
    
    # CRITICAL: Final context check right before LLM invocation
    # This ensures we catch any context growth during agent execution
    if agent_name == "pm_agent" and token_limit:
        # Re-count tokens right before invocation (context may have grown)
        final_token_count = context_manager.count_tokens(agent_input["messages"], model=model_name)
        logger.info(f"[{agent_name}] 🔍 Final token check before LLM: {final_token_count:,} tokens (limit: {token_limit:,}, message limit: {message_token_limit:,})")
        
        # If still over limit, apply emergency truncation
        if final_token_count > message_token_limit:
            logger.warning(
                f"[{agent_name}] 🚨 EMERGENCY: Context still over limit ({final_token_count:,} > {message_token_limit:,}) "
                f"right before LLM call. Applying emergency truncation..."
            )
            
            # Emergency truncation: truncate first message (contains completed_steps_info)
            if agent_input["messages"]:
                first_msg = agent_input["messages"][0]
                if hasattr(first_msg, 'content') and isinstance(first_msg.content, str):
                    # Calculate emergency max chars (reserve 15% for other messages and overhead)
                    emergency_max_chars = int((message_token_limit * 0.85) * 4)  # 85% of message tokens * 4 chars/token
                    if len(first_msg.content) > emergency_max_chars:
                        original_len = len(first_msg.content)
                        first_msg.content = first_msg.content[:emergency_max_chars] + "\n\n... (emergency truncation - context too large) ..."
                        logger.warning(
                            f"[{agent_name}] 🚨 Emergency truncated first message: {original_len:,} → {emergency_max_chars:,} chars"
                        )
                        
                        # Recalculate after emergency truncation
                        final_token_count = context_manager.count_tokens(agent_input["messages"], model=model_name)
                        logger.info(
                            f"[{agent_name}] 🔍 After emergency truncation: {final_token_count:,} tokens "
                            f"(message limit: {message_token_limit:,}, total limit: {token_limit:,})"
                        )
                        
                        # If STILL over limit, return error
                        if final_token_count > message_token_limit:
                            error_msg = (
                                f"❌ **Context Too Large for {agent_name}**\n\n"
                                f"The analysis data ({final_token_count:,} tokens) exceeds the model's limit ({token_limit:,} tokens).\n\n"
                                f"**Current model:** {model_name} (max {token_limit:,} tokens)\n\n"
                                f"**Solutions:**\n"
                                f"1. Switch to a larger model (GPT-4o, Claude 3.5 Sonnet)\n"
                                f"2. Request a more focused analysis with fewer steps\n"
                                f"3. Reduce the amount of data being analyzed"
                            )
                            logger.error(f"[{agent_name}] 🚨 Cannot proceed - context still too large after emergency truncation")
                            from src.prompts.planner_model import Step, Plan
                            updated_step = Step(
                                need_search=current_step.need_search,
                                title=current_step.title,
                                description=current_step.description,
                                step_type=current_step.step_type,
                                execution_res=error_msg,
                            )
                            updated_steps = list(current_plan.steps)
                            updated_steps[current_step_idx] = updated_step
                            updated_plan = Plan(
                                locale=current_plan.locale,
                                has_enough_context=current_plan.has_enough_context,
                                thought=current_plan.thought,
                                title=current_plan.title,
                                steps=updated_steps,
                            )
                            completed_count = sum(1 for step in updated_plan.steps if step.execution_res)
                            return Command(
                                update={
                                    "messages": [HumanMessage(content=error_msg, name=agent_name)],
                                    "observations": observations + [error_msg],
                                    "current_plan": updated_plan,
                                    "current_step_index": min(completed_count, len(updated_plan.steps) - 1),
                                },
                                goto="research_team",
                            )
        else:
            logger.info(f"[{agent_name}] ✅ Final token check passed: {final_token_count:,} tokens within limit")
    
    try:
        invoke_start_time = time.time()
        logger.info(f"[STEP-TIMING] Invoking agent '{agent_name}' for step '{current_step.title}' at {invoke_start_time}")
        
        # Log final token count for frontend tracking (if available)
        if agent_name == "pm_agent" and token_limit:
            final_count = context_manager.count_tokens(agent_input["messages"], model=model_name)
            logger.info(f"[{agent_name}] 📊 Context token count before LLM: {final_count:,} / {token_limit:,} tokens ({final_count/token_limit*100:.1f}%)")
        
        result = await agent.ainvoke(
            input=agent_input, config={"recursion_limit": recursion_limit}
        )
        invoke_end_time = time.time()
        invoke_duration = invoke_end_time - invoke_start_time
        logger.info(f"[STEP-TIMING] Agent '{agent_name}' completed in {invoke_duration:.2f}s (step: '{current_step.title}')")
        
        # Check if agent made tool calls
        last_message = result.get("messages", [])[-1] if result.get("messages") else None
        tool_calls_made = []
        response_preview = ""
        if last_message:
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                tool_calls_made = [tc.get('name', 'unknown') for tc in last_message.tool_calls]
            if hasattr(last_message, 'content'):
                response_preview = str(last_message.content)[:300]
        sys.stderr.write(f"\n✅ AGENT COMPLETED: agent_name='{agent_name}', tool_calls={tool_calls_made}\n")
        sys.stderr.write(f"✅ Response preview: {response_preview}...\n")
        sys.stderr.flush()
        
    except Exception as e:
        import traceback
        sys.stderr.write(f"\n❌ AGENT ERROR: agent_name='{agent_name}', error={str(e)}\n")
        sys.stderr.flush()

        error_traceback = traceback.format_exc()
        error_message = f"Error executing {agent_name} agent for step '{current_step.title}': {str(e)}"
        logger.exception(error_message)
        logger.error(f"Full traceback:\n{error_traceback}")
        
        # Enhanced error diagnostics for content-related errors
        if "Field required" in str(e) and "content" in str(e):
            logger.error(f"Message content validation error detected")
            for i, msg in enumerate(agent_input.get('messages', [])):
                logger.error(f"Message {i}: type={type(msg).__name__}, "
                            f"has_content={hasattr(msg, 'content')}, "
                            f"content_type={type(msg.content).__name__ if hasattr(msg, 'content') else 'N/A'}, "
                            f"content_len={len(str(msg.content)) if hasattr(msg, 'content') and msg.content else 0}")

        detailed_error = f"[ERROR] {agent_name.capitalize()} Agent Error\n\nStep: {current_step.title}\n\nError Details:\n{str(e)}\n\nPlease check the logs for more information."
        
        # CRITICAL: Create new Step and Plan objects instead of mutating in place
        from src.prompts.planner_model import Step, Plan
        
        # Use the stored index (set when finding the unexecuted step)
        # If for some reason it's not set, try to find it by title as fallback
        if current_step_idx is None:
            logger.warning(f"current_step_idx not set, searching by step title: {current_step.title}")
            for idx, step in enumerate(current_plan.steps):
                if step.title == current_step.title and not step.execution_res:
                    current_step_idx = idx
                    break
        
        if current_step_idx is not None:
            # Create a new Step with error in execution_res
            updated_step = Step(
                need_search=current_step.need_search,
                title=current_step.title,
                description=current_step.description,
                step_type=current_step.step_type,
                execution_res=detailed_error,  # Set the error as execution result
            )
            
            # Create a new list of steps with the updated step
            updated_steps = list(current_plan.steps)
            updated_steps[current_step_idx] = updated_step
            
            # Create a new Plan with updated steps
            updated_plan = Plan(
                locale=current_plan.locale,
                has_enough_context=current_plan.has_enough_context,
                thought=current_plan.thought,
                title=current_plan.title,
                steps=updated_steps,
            )

        # Calculate the current step index even on error
            completed_count = sum(1 for step in updated_plan.steps if step.execution_res)
            current_step_index = min(completed_count, len(updated_plan.steps) - 1)
        else:
            logger.error(f"Could not find current step '{current_step.title}' in plan steps")
            updated_plan = current_plan
            current_step_index = 0

        # CRITICAL: Include updated_plan in the update to ensure LangGraph persists the state change
        return Command(
            update={
                "messages": [
                    HumanMessage(
                        content=detailed_error,
                        name=agent_name,
                    )
                ],
                "observations": observations + [detailed_error],
                "current_step_index": current_step_index,  # Update step progress even on error
                "current_plan": updated_plan,  # Include new plan object with updated step execution_res
            },
            goto="research_team",
        )

    # Process the result
    response_content = result["messages"][-1].content
    
    # Extract tool results from ToolMessage objects to include in execution result
    # This ensures the reporter has access to actual tool data, not just the agent's summary
    tool_results = []
    tool_calls_info = []
    
    # Log all messages to debug tool call results
    logger.debug(f"[{agent_name}] All messages in result: {len(result.get('messages', []))}")
    for i, msg in enumerate(result.get("messages", [])):
        msg_type = type(msg).__name__
        if msg_type == "ToolMessage":
            tool_call_id = getattr(msg, 'tool_call_id', 'N/A')
            tool_content = str(msg.content)
            logger.info(f"[{agent_name}] Message {i}: ToolMessage - tool_call_id={tool_call_id}, content_len={len(tool_content)}")
            
            # Extract tool name from tool_call_id if possible, or use a generic identifier
            # Try to find the corresponding AIMessage with tool_calls to get the tool name
            tool_name = "unknown_tool"
            for prev_msg in result.get("messages", [])[:i]:
                if hasattr(prev_msg, 'tool_calls') and prev_msg.tool_calls:
                    for tc in prev_msg.tool_calls:
                        if tc.get('id') == tool_call_id:
                            tool_name = tc.get('name', 'unknown_tool')
                            break
                    if tool_name != "unknown_tool":
                        break
            
            # CRITICAL: Sanitize each tool result with aggressive truncation for PM agent context
            # PM agent has 16K token limit, so we need to keep tool responses very small
            # Use max_length=10000 (≈2500 tokens) per tool response to leave room for other content
            # Note: sanitize_tool_response is imported at module level (line 36)
            max_tool_response_length = 10000  # 10K chars ≈ 2.5K tokens
            # Import with alias to avoid UnboundLocalError (Python sees it as local if imported in function)
            import src.utils.json_utils as json_utils_module
            sanitized_tool_content = json_utils_module.sanitize_tool_response(
                str(tool_content), 
                max_length=max_tool_response_length,
                compress_arrays=True
            )
            tool_results.append(f"### Tool: {tool_name}\n\n{sanitized_tool_content}")
            tool_calls_info.append(f"{tool_name}: {len(tool_content)}→{len(sanitized_tool_content)} chars")
        
        elif msg_type == "AIMessage":
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                logger.info(f"[{agent_name}] Message {i}: AIMessage with {len(msg.tool_calls)} tool calls: {[tc.get('name', 'N/A') for tc in msg.tool_calls]}")
                
                # Thoughts come directly from OpenAI response - no extraction needed
                # OpenAI response already has reasoning in:
                # 1. reasoning_content field (for o1 models) - already in additional_kwargs
                # 2. response_metadata.react_thoughts (if LangChain/LangGraph attached it)
                # 3. additional_kwargs.react_thoughts (if already set)
                # We just read what's already there, don't extract
                if agent_name == "pm_agent":
                    # Check if thoughts are already in the message from OpenAI response
                    existing_thoughts = None
                    if hasattr(msg, 'response_metadata') and msg.response_metadata:
                        existing_thoughts = msg.response_metadata.get("react_thoughts")
                    if not existing_thoughts and hasattr(msg, 'additional_kwargs') and msg.additional_kwargs:
                        existing_thoughts = msg.additional_kwargs.get("react_thoughts")
                    
                    if existing_thoughts:
                        logger.info(f"[{agent_name}] 💭 Found {len(existing_thoughts)} thoughts in OpenAI response (already attached)")
                    else:
                        logger.debug(f"[{agent_name}] No thoughts found in OpenAI response - agent may not have included reasoning")
            else:
                logger.debug(f"[{agent_name}] Message {i}: AIMessage - content={str(msg.content)[:200]}")
        else:
            logger.debug(f"[{agent_name}] Message {i}: {msg_type} - content={str(msg.content)[:200] if hasattr(msg, 'content') else 'N/A'}")
    
    # Combine agent response with tool results
    if tool_results:
        logger.info(f"[{agent_name}] Including {len(tool_results)} tool results in execution result: {', '.join(tool_calls_info)}")
        # Format: Agent summary first, then tool results
        combined_result = f"{response_content}\n\n## Tool Call Results\n\n" + "\n\n".join(tool_results)
    else:
        combined_result = response_content
    
    # Final sanitization pass on combined result to ensure it's within limits
    # Use model-aware max_length based on token limit
    # Reserve 30% for prompt, use remaining for execution result
    if token_limit:
        max_execution_result_length = int((token_limit * 0.7) * 4)  # 70% of tokens * 4 chars/token
        max_execution_result_length = min(max_execution_result_length, 50000)  # Cap at 50K chars
    else:
        max_execution_result_length = 20000  # Default 20K chars ≈ 5K tokens
    
    # Use module import to avoid UnboundLocalError
    import src.utils.json_utils as json_utils_module
    combined_result = json_utils_module.sanitize_tool_response(
        str(combined_result),
        max_length=max_execution_result_length,
        compress_arrays=True
    )
    logger.info(f"[{agent_name}] Final execution result length: {len(combined_result)} chars (max={max_execution_result_length}, token_limit={token_limit})")
    
    logger.debug(f"{agent_name.capitalize()} full response: {combined_result[:500]}...")

    # CRITICAL: Create new Step and Plan objects instead of mutating in place
    # Pydantic models and LangGraph state updates require creating new objects
    # to properly detect state changes
    from src.prompts.planner_model import Step, Plan
    
    # Use the stored index (set when finding the unexecuted step)
    if current_step_idx is None:
        logger.error(f"Could not find current step '{current_step.title}' in plan steps (index not set)")
        return Command(goto="research_team")
    
    # Create a new Step with updated execution_res
    updated_step = Step(
        need_search=current_step.need_search,
        title=current_step.title,
        description=current_step.description,
        step_type=current_step.step_type,
        execution_res=combined_result,  # Set the execution result
    )
    
    # Create a new list of steps with the updated step
    updated_steps = list(current_plan.steps)
    updated_steps[current_step_idx] = updated_step
    
    # Create a new Plan with updated steps
    updated_plan = Plan(
        locale=current_plan.locale,
        has_enough_context=current_plan.has_enough_context,
        thought=current_plan.thought,
        title=current_plan.title,
        steps=updated_steps,
    )
    
    logger.info(f"Step '{current_step.title}' execution completed by {agent_name}")

    # Calculate the current step index (number of completed steps)
    completed_count = sum(1 for step in updated_plan.steps if step.execution_res)
    current_step_index = min(completed_count, len(updated_plan.steps) - 1)
    logger.info(f"Step progress: {completed_count}/{len(updated_plan.steps)} steps completed (current_step_index={current_step_index})")

    sys.stderr.write(f"\n🔄 RETURNING RESULT: agent_name='{agent_name}', message_type='AIMessage', content_len={len(combined_result)}\n")
    sys.stderr.write(f"🔄 Step '{current_step.title}' execution_res set: {bool(updated_step.execution_res)}\n")
    sys.stderr.write(f"🔄 Updated plan has {completed_count} completed steps out of {len(updated_plan.steps)}\n")
    sys.stderr.flush()
    
    # Collect thoughts from PM Agent's actual reasoning (not plan step descriptions)
    # CRITICAL: Only use thoughts from agent's reasoning, which matches what the agent actually does
    pm_thoughts = []
    
    # Read thoughts directly from OpenAI response - they're already in the message
    # No extraction needed - OpenAI response already has reasoning in response_metadata or additional_kwargs
    for msg in result.get("messages", []):
        if isinstance(msg, AIMessage):
            # Check response_metadata first (most reliable, from OpenAI)
            if hasattr(msg, 'response_metadata') and msg.response_metadata:
                msg_thoughts = msg.response_metadata.get("react_thoughts", [])
                if msg_thoughts:
                    pm_thoughts = msg_thoughts
                    logger.info(f"[{agent_name}] 💭 Found {len(msg_thoughts)} thoughts in OpenAI response (response_metadata)")
                    break
            
            # Check additional_kwargs (backup location)
            if not pm_thoughts and hasattr(msg, 'additional_kwargs') and msg.additional_kwargs:
                msg_thoughts = msg.additional_kwargs.get("react_thoughts", [])
                if msg_thoughts:
                    pm_thoughts = msg_thoughts
                    logger.info(f"[{agent_name}] 💭 Found {len(msg_thoughts)} thoughts in OpenAI response (additional_kwargs)")
                    break
    
    if not pm_thoughts:
        logger.debug(f"[{agent_name}] No thoughts found in OpenAI response - agent may not have included reasoning")
    
    # Include optimization messages if they exist
    final_message = AIMessage(
        content=response_content,
        name=agent_name,
    )
    
    # CRITICAL: Attach thoughts to the final message so they're available when streamed
    # Thoughts are independent of tool_calls - they're the agent's reasoning
    if pm_thoughts:
        if not hasattr(final_message, 'additional_kwargs') or not final_message.additional_kwargs:
            final_message.additional_kwargs = {}
        if not hasattr(final_message, 'response_metadata') or not final_message.response_metadata:
            final_message.response_metadata = {}
        final_message.additional_kwargs["react_thoughts"] = pm_thoughts
        final_message.response_metadata["react_thoughts"] = pm_thoughts
        logger.info(f"[{agent_name}] 💭 Attached {len(pm_thoughts)} thoughts to final message for streaming")
    
    return_messages = [final_message]
    optimization_messages = state.get("_optimization_messages", [])
    if optimization_messages:
        return_messages = optimization_messages + return_messages
        # Clear from state after use
        state.pop("_optimization_messages", None)
    
    # CRITICAL: Include updated_plan in the update to ensure LangGraph persists the state change
    # Also include thoughts in state for backend streaming
    update_dict = {
        "messages": return_messages,
        "observations": observations + [response_content],
        "current_step_index": current_step_index,  # Update step progress
        "current_plan": updated_plan,  # Include new plan object with updated step execution_res
    }
    
    # Add thoughts to state for PM Agent (for backend streaming)
    if agent_name == "pm_agent" and pm_thoughts:
        update_dict["react_thoughts"] = pm_thoughts
        logger.info(f"[{agent_name}] 💭 Added {len(pm_thoughts)} thoughts to state update")
    
    return Command(
        update=update_dict,
        goto="research_team",
    )


async def _setup_and_execute_agent_step(
    state: State,
    config: RunnableConfig,
    agent_type: str,
    default_tools: list[Any],
) -> Command[Literal["research_team"]]:
    """Helper function to set up an agent with appropriate tools and execute a step.

    This function handles the common logic for both researcher_node and coder_node:
    1. Configures MCP servers and tools based on agent type
    2. Creates an agent with the appropriate tools or uses the default agent
    3. Executes the agent on the current step

    Args:
        state: The current state
        config: The runnable config
        agent_type: The type of agent ("researcher" or "coder")
        default_tools: The default tools to add to the agent

    Returns:
        Command to update state and go to research_team
    """
    configurable = Configuration.from_runnable_config(config)
    
    # Debug logging for mcp_settings
    logger.info(
        f"[{agent_type}] Configuration.mcp_settings: {configurable.mcp_settings is not None}, "
        f"type: {type(configurable.mcp_settings).__name__}"
    )
    if configurable.mcp_settings:
        logger.info(
            f"[{agent_type}] mcp_settings keys: {list(configurable.mcp_settings.keys()) if isinstance(configurable.mcp_settings, dict) else 'N/A'}"
        )
        if isinstance(configurable.mcp_settings, dict) and "servers" in configurable.mcp_settings:
            logger.info(
                f"[{agent_type}] mcp_settings['servers'] keys: {list(configurable.mcp_settings['servers'].keys())}"
            )
            for server_name, server_config in configurable.mcp_settings["servers"].items():
                logger.info(
                    f"[{agent_type}] Server '{server_name}' in mcp_settings: transport={server_config.get('transport')}, "
                    f"has_url={'url' in server_config}, has_command={'command' in server_config}"
                )
    
    mcp_servers = {}
    enabled_tools = {}

    # Extract MCP server configuration for this agent type
    if configurable.mcp_settings:
        logger.info(f"[{agent_type}] Processing MCP settings for agent")
        for server_name, server_config in configurable.mcp_settings["servers"].items():
            logger.info(f"[{agent_type}] Checking server '{server_name}', add_to_agents={server_config.get('add_to_agents')}")
            # Check if this agent should use this MCP server
            # enabled_tools can be None (all tools), empty list (no tools), or list of specific tools
            if agent_type in server_config["add_to_agents"]:
                logger.info(f"[{agent_type}] Agent IS in add_to_agents for '{server_name}'")
                enabled_tools_config = server_config["enabled_tools"]
                logger.info(f"[{agent_type}] enabled_tools_config={enabled_tools_config}, type={type(enabled_tools_config)}")
                # Skip if explicitly set to empty list (no tools)
                if enabled_tools_config is not None and len(enabled_tools_config) == 0:
                    logger.info(f"[{agent_type}] Skipping server '{server_name}' - enabled_tools is empty list")
                    continue
                    
                logger.info(f"[{agent_type}] Adding server '{server_name}' to mcp_servers")
                mcp_servers[server_name] = {
                    k: v
                    for k, v in server_config.items()
                    if k in ("transport", "command", "args", "url", "env", "headers")
                }
                # If enabled_tools is None, we'll enable all tools from this server
                # If it's a list, we'll only enable those specific tools
                if enabled_tools_config is not None:
                    logger.info(f"[{agent_type}] Adding {len(enabled_tools_config)} specific tools to enabled_tools")
                    for tool_name in enabled_tools_config:
                        enabled_tools[tool_name] = server_name
                else:
                    logger.info(f"[{agent_type}] enabled_tools is None - will enable ALL tools from '{server_name}'")
                # If None, we don't populate enabled_tools here - all tools will be added later
            else:
                logger.info(f"[{agent_type}] Agent NOT in add_to_agents for '{server_name}'")
        
        logger.info(f"[{agent_type}] After processing: mcp_servers={list(mcp_servers.keys())}, enabled_tools count={len(enabled_tools)}")

    # Create and execute agent with MCP tools if available
    if mcp_servers:
        try:
            logger.info(
                f"[{agent_type}] Connecting to {len(mcp_servers)} MCP server(s): "
                f"{', '.join(mcp_servers.keys())}"
            )
            # Detailed logging of each server config
            for server_name, server_config in mcp_servers.items():
                logger.info(
                    f"[{agent_type}] Server '{server_name}' config: transport={server_config.get('transport')}, "
                    f"has_url={'url' in server_config}, has_command={'command' in server_config}, "
                    f"has_headers={'headers' in server_config}, config_keys={list(server_config.keys())}"
                )
                if 'url' in server_config:
                    logger.info(f"[{agent_type}] Server '{server_name}' URL: {server_config['url']}")
                if 'headers' in server_config:
                    headers = server_config['headers']
                    # Log headers but mask sensitive values
                    masked_headers = {k: (v[:10] + '...' if len(v) > 10 else v) if k == 'X-MCP-API-Key' else v 
                                     for k, v in headers.items()}
                    logger.info(f"[{agent_type}] Server '{server_name}' headers: {masked_headers}")
                if 'transport' in server_config:
                    logger.info(f"[{agent_type}] Server '{server_name}' transport type: {type(server_config['transport']).__name__}, value: {repr(server_config['transport'])}")
            logger.info(
                f"[{agent_type}] MCP server configs: {json.dumps(mcp_servers, indent=2, default=str)}"
            )
            logger.info(f"[{agent_type}] Creating MultiServerMCPClient with {len(mcp_servers)} server(s)...")
            # Log the exact dict being passed
            logger.info(f"[{agent_type}] Passing to MultiServerMCPClient: {json.dumps(mcp_servers, indent=2, default=str)}")
            
            # Create MCP client with timeout protection
            try:
                # MultiServerMCPClient constructor should be fast, but wrap in timeout just in case
                client = MultiServerMCPClient(mcp_servers)
                logger.info(f"[{agent_type}] MultiServerMCPClient created. Checking connections...")
            except Exception as client_error:
                logger.error(
                    f"[{agent_type}] Failed to create MultiServerMCPClient: {client_error}. "
                    "Continuing without MCP tools.",
                    exc_info=True
                )
                all_tools = []
                loaded_tools = default_tools[:]
                # Skip to agent creation without MCP tools
                agent = create_agent(
                    agent_type,
                    agent_type,
                    loaded_tools,
                    agent_type,
                    pre_model_hook,
                    interrupt_before_tools=configurable.interrupt_before_tools,
                )
                return await _execute_agent_step(state, agent, agent_type)
            # Verify what connections were actually stored
            for server_name, connection in client.connections.items():
                logger.info(
                    f"[{agent_type}] Stored connection '{server_name}': transport={connection.get('transport')}, "
                    f"has_url={'url' in connection}, keys={list(connection.keys())}, "
                    f"connection_type={type(connection).__name__}"
                )
                # Deep inspection of the connection
                if isinstance(connection, dict):
                    logger.info(
                        f"[{agent_type}] Connection '{server_name}' dict contents: {json.dumps(connection, indent=2, default=str)}"
                    )
            loaded_tools = default_tools[:]
            logger.info(f"[DEBUG-NODES] [MCP-5] [{agent_type}] About to call client.get_tools()...")
            
            # Add timeout to prevent hanging on MCP server connection
            mcp_timeout = 30  # 30 seconds timeout for MCP connection
            try:
                logger.info(f"[DEBUG-NODES] [MCP-6] [{agent_type}] Calling asyncio.wait_for(client.get_tools(), timeout={mcp_timeout})")
                all_tools = await asyncio.wait_for(
                    client.get_tools(),
                    timeout=mcp_timeout
                )
                logger.info(f"[DEBUG-NODES] [MCP-7] [{agent_type}] client.get_tools() completed successfully")
                logger.info(
                    f"[{agent_type}] Retrieved {len(all_tools)} tools from MCP servers"
                )
            except asyncio.TimeoutError:
                logger.error(
                    f"[{agent_type}] MCP server connection timed out after {mcp_timeout}s. "
                    "Continuing without MCP tools."
                )
                all_tools = []
            except Exception as mcp_error:
                logger.error(
                    f"[{agent_type}] Failed to connect to MCP server: {mcp_error}. "
                    "Continuing without MCP tools.",
                    exc_info=True
                )
                all_tools = []
            logger.info(
                f"[{agent_type}] MCP tool names: {[tool.name for tool in all_tools]}"
            )
            logger.info(
                f"[{agent_type}] Enabled tools filter: {list(enabled_tools.keys())}"
            )
            # Check if list_my_tasks is in the discovered tools
            list_my_tasks_found = any(tool.name == "list_my_tasks" for tool in all_tools)
            logger.info(
                f"[{agent_type}] list_my_tasks tool found: {list_my_tasks_found}"
            )
            if not list_my_tasks_found:
                logger.warning(
                    f"[{agent_type}] WARNING: list_my_tasks tool NOT found in discovered tools! "
                    f"Available tools: {[tool.name for tool in all_tools]}"
                )
            
            # CRITICAL: Wrap MCP tools with truncation to prevent token overflow
            from src.utils.json_utils import sanitize_tool_response
            from langchain_core.tools import BaseTool
            import inspect
            
            def wrap_mcp_tool_with_truncation(tool: BaseTool, max_tokens: int = 1000, timeout_seconds: int = 120) -> BaseTool:
                """Wrap an MCP tool to truncate its output and add timeout protection."""
                max_chars = max_tokens * 4  # 4 chars per token
                
                # Get the original tool function
                if hasattr(tool, 'func'):
                    original_func = tool.func
                elif hasattr(tool, '_run'):
                    original_func = tool._run
                else:
                    return tool  # Can't wrap, return as-is
                
                # Check if it's async
                is_async = inspect.iscoroutinefunction(original_func)
                
                if is_async:
                    async def truncated_func(*args, **kwargs):
                        try:
                            # Add timeout protection
                            result = await asyncio.wait_for(
                                original_func(*args, **kwargs),
                                timeout=timeout_seconds
                            )
                        except asyncio.TimeoutError:
                            error_msg = f"MCP Tool '{tool.name}' timed out after {timeout_seconds} seconds"
                            logger.error(f"[{agent_type}] ⏱️ {error_msg}")
                            return f"Error: {error_msg}. The tool execution took too long and was cancelled."
                        except Exception as e:
                            error_msg = f"Error executing MCP tool '{tool.name}': {str(e)}"
                            logger.error(f"[{agent_type}] ❌ {error_msg}", exc_info=True)
                            return f"Error: {error_msg}"
                        
                        result_str = str(result)
                        original_len = len(result_str)
                        
                        if original_len > max_chars:
                            logger.warning(
                                f"[{agent_type}] 🔍 MCP Tool '{tool.name}' returned {original_len:,} chars "
                                f"(≈{original_len//4:,} tokens). Truncating to {max_chars:,} chars (≈{max_tokens:,} tokens)."
                            )
                            result_str = sanitize_tool_response(result_str, max_length=max_chars, compress_arrays=True)
                            final_len = len(result_str)
                            logger.info(
                                f"[{agent_type}] ✅ MCP Tool '{tool.name}' truncated: {original_len:,} → {final_len:,} chars "
                                f"(≈{original_len//4:,} → ≈{final_len//4:,} tokens)"
                            )
                        return result_str
                    
                    if hasattr(tool, 'func'):
                        tool.func = truncated_func
                    elif hasattr(tool, '_run'):
                        tool._run = truncated_func
                else:
                    async def truncated_func(*args, **kwargs):
                        try:
                            # For sync functions, run in executor with timeout
                            import concurrent.futures
                            loop = asyncio.get_event_loop()
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(original_func, *args, **kwargs)
                                result = await asyncio.wait_for(
                                    asyncio.wrap_future(future),
                                    timeout=timeout_seconds
                                )
                        except asyncio.TimeoutError:
                            error_msg = f"MCP Tool '{tool.name}' timed out after {timeout_seconds} seconds"
                            logger.error(f"[{agent_type}] ⏱️ {error_msg}")
                            return f"Error: {error_msg}. The tool execution took too long and was cancelled."
                        except Exception as e:
                            error_msg = f"Error executing MCP tool '{tool.name}': {str(e)}"
                            logger.error(f"[{agent_type}] ❌ {error_msg}", exc_info=True)
                            return f"Error: {error_msg}"
                        
                        result_str = str(result)
                        original_len = len(result_str)
                        
                        if original_len > max_chars:
                            logger.warning(
                                f"[{agent_type}] 🔍 MCP Tool '{tool.name}' returned {original_len:,} chars "
                                f"(≈{original_len//4:,} tokens). Truncating to {max_chars:,} chars (≈{max_tokens:,} tokens)."
                            )
                            result_str = sanitize_tool_response(result_str, max_length=max_chars, compress_arrays=True)
                            final_len = len(result_str)
                            logger.info(
                                f"[{agent_type}] ✅ MCP Tool '{tool.name}' truncated: {original_len:,} → {final_len:,} chars "
                                f"(≈{original_len//4:,} → ≈{final_len//4:,} tokens)"
                            )
                        return result_str
                    
                    if hasattr(tool, 'func'):
                        tool.func = truncated_func
                    elif hasattr(tool, '_run'):
                        tool._run = truncated_func
                
                return tool
            
            added_count = 0
            list_my_tasks_added = False
            for tool in all_tools:
                # If enabled_tools is empty, enable ALL tools from all connected servers
                # Otherwise, only enable tools that are in the enabled_tools dict
                if not enabled_tools or tool.name in enabled_tools:
                    server_name = enabled_tools.get(tool.name, "unknown") if enabled_tools else list(mcp_servers.keys())[0] if mcp_servers else "unknown"
                    tool.description = (
                        f"Powered by '{server_name}'.\n{tool.description}"
                    )
                    # CRITICAL: Wrap tool with truncation before adding
                    tool = wrap_mcp_tool_with_truncation(tool, max_tokens=1000)
                    loaded_tools.append(tool)
                    added_count += 1
                    if tool.name == "list_my_tasks":
                        list_my_tasks_added = True
                    logger.info(
                        f"[{agent_type}] Added MCP tool: {tool.name} "
                        f"(from {server_name}, with truncation)"
                    )
            
            import sys
            sys.stderr.write(f"\n🔧 [{agent_type}] TOOLS LOADED: {added_count} MCP tools added (total: {len(loaded_tools)})\n")
            sys.stderr.write(f"🔧 [{agent_type}] Tool names: {[tool.name for tool in loaded_tools]}\n")
            sys.stderr.flush()
            logger.info(
                f"[{agent_type}] Added {added_count} MCP tools to agent "
                f"(total tools: {len(loaded_tools)})"
            )
            logger.info(
                f"[{agent_type}] list_my_tasks tool added to agent: {list_my_tasks_added}"
            )
            if not list_my_tasks_added:
                sys.stderr.write(f"\n❌ [{agent_type}] ERROR: list_my_tasks NOT ADDED!\n")
                sys.stderr.flush()
                logger.error(
                    f"[{agent_type}] ERROR: list_my_tasks tool was NOT added to agent! "
                    f"This means the tool was either not discovered or not in enabled_tools filter."
                )
        except Exception as e:
            logger.error(
                f"[{agent_type}] Failed to load MCP tools: {e}",
                exc_info=True
            )
            # Instead of raising RuntimeError (which stops the workflow), handle gracefully
            # by creating an error step and routing to reporter
            error_message = (
                f"[ERROR] Failed to load PM tools from MCP server: {e}. "
                "Cannot proceed without PM tools. Please ensure the MCP server is running and accessible."
            )
            logger.error(error_message)
            
            # Get current plan and mark current step as failed
            current_plan = state.get("current_plan")
            if current_plan and not isinstance(current_plan, str) and hasattr(current_plan, 'steps'):
                from src.prompts.planner_model import Step, Plan
                
                # Find first incomplete step
                current_step_idx = None
                for idx, step in enumerate(current_plan.steps):
                    if not step.execution_res:
                        current_step_idx = idx
                        break
                
                if current_step_idx is not None:
                    # Mark step as failed
                    updated_step = Step(
                        need_search=current_plan.steps[current_step_idx].need_search,
                        title=current_plan.steps[current_step_idx].title,
                        description=current_plan.steps[current_step_idx].description,
                        step_type=current_plan.steps[current_step_idx].step_type,
                        execution_res=error_message,
                    )
                    updated_steps = list(current_plan.steps)
                    updated_steps[current_step_idx] = updated_step
                    updated_plan = Plan(
                        locale=current_plan.locale,
                        has_enough_context=current_plan.has_enough_context,
                        thought=current_plan.thought,
                        title=current_plan.title,
                        steps=updated_steps,
                    )
                    
                    # Check if all steps are done (including failed ones)
                    all_done = all(step.execution_res for step in updated_plan.steps)
                    return Command(
                        update={
                            "messages": [HumanMessage(content=error_message, name=agent_type)],
                            "observations": state.get("observations", []) + [error_message],
                            "current_plan": updated_plan,
                        },
                        goto="reporter" if all_done else "research_team",
                    )
            
            # Fallback: route to reporter with error
            return Command(
                update={
                    "messages": [HumanMessage(content=error_message, name=agent_type)],
                    "observations": state.get("observations", []) + [error_message],
                },
                goto="reporter",
            )

        # Use agent-specific context strategy for better compression
        # Account for frontend history to coordinate token budgets
        from src.utils.agent_context_config import get_context_manager_for_agent
        
        # Extract frontend history messages for token budgeting
        frontend_count = state.get("frontend_history_message_count", 0)
        all_messages = list(state.get("messages", []))
        
        # Frontend history is the first N messages (before agent's additions)
        frontend_messages = all_messages[:frontend_count] if frontend_count > 0 else []
        
        # Get context manager with adjusted token limit
        context_manager = get_context_manager_for_agent(
            agent_type,
            frontend_history_messages=frontend_messages
        )
        
        # Create pre_model_hook that captures optimization metadata
        # Store optimization messages in state for later inclusion in Command return
        def compress_with_tracking(state_dict):
            compressed = context_manager.compress_messages(state_dict)
            optimization_metadata = compressed.get("_context_optimization") if isinstance(compressed, dict) else None
            if optimization_metadata:
                opt_messages = _add_context_optimization_tool_call(state, agent_type, optimization_metadata)
                if opt_messages:
                    state["_optimization_messages"] = opt_messages
            return compressed
        
        pre_model_hook = compress_with_tracking
        agent = create_agent(
            agent_type,
            agent_type,
            loaded_tools,
            agent_type,
            pre_model_hook,
            interrupt_before_tools=configurable.interrupt_before_tools,
        )
        return await _execute_agent_step(state, agent, agent_type)
    else:
        # Use default tools if no MCP servers are configured
        try:
            llm_token_limit = get_llm_token_limit_by_type(AGENT_LLM_MAP[agent_type])
            context_manager_default = ContextManager(llm_token_limit, 3, agent_type=agent_type)
            
            # Create pre_model_hook that captures optimization metadata
            # Store optimization messages in state for later inclusion in Command return
            def compress_with_tracking_default(state_dict):
                compressed = context_manager_default.compress_messages(state_dict)
                optimization_metadata = compressed.get("_context_optimization") if isinstance(compressed, dict) else None
                if optimization_metadata:
                    opt_messages = _add_context_optimization_tool_call(state, agent_type, optimization_metadata)
                    if opt_messages:
                        state["_optimization_messages"] = opt_messages
                return compressed
            
            pre_model_hook = compress_with_tracking_default
            agent = create_agent(
                agent_type,
                agent_type,
                default_tools,
                agent_type,
                pre_model_hook,
                interrupt_before_tools=configurable.interrupt_before_tools,
            )
            return await _execute_agent_step(state, agent, agent_type)
        except Exception as e:
            logger.error(
                f"[{agent_type}] Failed to create agent or execute step: {e}",
                exc_info=True
            )
            # Handle error gracefully by marking step as failed and routing appropriately
            error_message = f"[ERROR] {agent_type.capitalize()} agent failed: {str(e)}"
            
            current_plan = state.get("current_plan")
            if current_plan and not isinstance(current_plan, str) and hasattr(current_plan, 'steps'):
                from src.prompts.planner_model import Step, Plan
                
                # Find first incomplete step
                current_step_idx = None
                for idx, step in enumerate(current_plan.steps):
                    if not step.execution_res:
                        current_step_idx = idx
                        break
                
                if current_step_idx is not None:
                    # Mark step as failed
                    updated_step = Step(
                        need_search=current_plan.steps[current_step_idx].need_search,
                        title=current_plan.steps[current_step_idx].title,
                        description=current_plan.steps[current_step_idx].description,
                        step_type=current_plan.steps[current_step_idx].step_type,
                        execution_res=error_message,
                    )
                    updated_steps = list(current_plan.steps)
                    updated_steps[current_step_idx] = updated_step
                    updated_plan = Plan(
                        locale=current_plan.locale,
                        has_enough_context=current_plan.has_enough_context,
                        thought=current_plan.thought,
                        title=current_plan.title,
                        steps=updated_steps,
                    )
                    
                    # Check if all steps are done (including failed ones)
                    all_done = all(step.execution_res for step in updated_plan.steps)
                    return Command(
                        update={
                            "messages": [HumanMessage(content=error_message, name=agent_type)],
                            "observations": state.get("observations", []) + [error_message],
                            "current_plan": updated_plan,
                        },
                        goto="reporter" if all_done else "research_team",
                    )
            
            # Fallback: route to reporter with error
            return Command(
                update={
                    "messages": [HumanMessage(content=error_message, name=agent_type)],
                    "observations": state.get("observations", []) + [error_message],
                },
                goto="reporter",
            )


async def researcher_node(
    state: State, config: RunnableConfig
) -> Command[Literal["research_team"]]:
    """Researcher node that do research"""
    logger.info(f"[DEBUG-NODES] [NODE-RESEARCHER-1] Researcher node entered")
    logger.info("Researcher node is researching.")
    logger.debug(f"[researcher_node] Starting researcher agent")
    
    configurable = Configuration.from_runnable_config(config)
    logger.debug(f"[researcher_node] Max search results: {configurable.max_search_results}")
    
    tools = [get_web_search_tool(configurable.max_search_results, provider_id=configurable.search_provider), crawl_tool, backend_api_call]
    retriever_tool = get_retriever_tool(state.get("resources", []))
    if retriever_tool:
        logger.debug(f"[researcher_node] Adding retriever tool to tools list")
        tools.insert(0, retriever_tool)
    
    # PM tools are loaded via MCP configuration in _setup_and_execute_agent_step
    # No need to manually add PM tools here
    
    # NOTE: Analytics tools are temporarily disabled because they conflict with MCP PM tools
    # The LLM prefers calling analytics tools (get_sprint_report, get_team_velocity, etc.)
    # but these tools fail because there's no analytics adapter configured.
    # The actual working tools are the MCP PM tools (list_sprints, list_tasks, get_sprint)
    # which are loaded via MCP configuration below.
    #
    # TODO: Either fix analytics tools to work as wrappers around MCP tools,
    # or improve MCP tool descriptions so LLM understands when to use them.
    
    # # Add Analytics tools for project insights
    # try:
    #     analytics_tools = get_analytics_tools()
    #     if analytics_tools:
    #         tools.extend(analytics_tools)
    #         logger.info(f"[researcher_node] Added {len(analytics_tools)} analytics tools to researcher agent")
    #         logger.debug(f"[researcher_node] Analytics tools: {[tool.name if hasattr(tool, 'name') else str(tool) for tool in analytics_tools]}")
    # except Exception as e:
    #     logger.warning(f"[researcher_node] Could not add analytics tools: {e}")
    
    logger.info(f"[researcher_node] Researcher tools count: {len(tools)}")
    logger.debug(f"[researcher_node] Researcher tools: {[tool.name if hasattr(tool, 'name') else str(tool) for tool in tools]}")
    
    return await _setup_and_execute_agent_step(
        state,
        config,
        "researcher",
        tools,
    )


async def coder_node(
    state: State, config: RunnableConfig
) -> Command[Literal["research_team"]]:
    """Coder node that do code analysis."""
    logger.info("Coder node is coding.")
    logger.debug(f"[coder_node] Starting coder agent with python_repl_tool")
    
    tools = [python_repl_tool, backend_api_call]
    
    # PM tools are loaded via MCP configuration in _setup_and_execute_agent_step
    # No need to manually add PM tools here
    
    # NOTE: Analytics tools are temporarily disabled (same reason as researcher_node)
    # # Add Analytics tools for data analysis
    # try:
    #     analytics_tools = get_analytics_tools()
    #     if analytics_tools:
    #         tools.extend(analytics_tools)
    #         logger.info(f"[coder_node] Added {len(analytics_tools)} analytics tools to coder agent")
    #         logger.debug(f"[coder_node] Analytics tools: {[tool.name if hasattr(tool, 'name') else str(tool) for tool in analytics_tools]}")
    # except Exception as e:
    #     logger.warning(f"[coder_node] Could not add analytics tools: {e}")
    
    return await _setup_and_execute_agent_step(
        state,
        config,
        "coder",
        tools,
    )


def validator_node(state: State, config: RunnableConfig) -> Command:
    """
    Validates the last executed step and decides next action.
    
    Uses LLM to analyze execution results and determine if the step succeeded,
    partially succeeded, or failed. Routes accordingly:
    - success/partial: Continue to next step (research_team)
    - failure: Route to reflection for replanning
    """
    logger.info("[VALIDATOR] Validating last executed step")
    
    current_plan = state.get("current_plan")
    current_step_index = state.get("current_step_index", 0)
    
    # Get the step that was just executed
    if not current_plan or isinstance(current_plan, str):
        logger.warning("[VALIDATOR] No valid plan found, routing to research_team")
        return Command(goto="research_team")
    
    # CRITICAL: Check if reporter already completed (prevent infinite loop)
    if state.get("final_report"):
        logger.info("[VALIDATOR] Reporter already completed (final_report exists). Workflow should end.")
        # Don't route anywhere - let the graph edge handle END
        return Command(
            update={
                "validation_results": state.get("validation_results", [])
            },
            goto="__end__"  # Route to END to stop the workflow
        )
    
    # CRITICAL: Check if all steps are complete FIRST (before finding last completed step)
    # This prevents the validator from processing steps that are already all done
    all_steps_complete = all(step.execution_res for step in current_plan.steps) if current_plan.steps else False
    if all_steps_complete:
        # CRITICAL: Check if reporter already completed BEFORE routing to reporter
        if state.get("final_report"):
            logger.info(f"[VALIDATOR] 🔍 DEBUG: All {len(current_plan.steps)} steps complete, but reporter already finished. Routing to __end__.")
            return Command(
                update={
                    "validation_results": state.get("validation_results", [])
                },
                goto="__end__"  # Don't route to reporter if it's already done
            )
        logger.info(f"[VALIDATOR] 🔍 DEBUG: All {len(current_plan.steps)} steps already have execution_res. Routing directly to reporter.")
        return Command(
            update={
                "validation_results": state.get("validation_results", [])
            },
            goto="reporter"
        )
    
    if not current_plan.steps or current_step_index >= len(current_plan.steps):
        logger.info("[VALIDATOR] No steps or step index out of range, routing to reporter")
        return Command(goto="reporter")
    
    # Find the most recently completed step
    last_completed_step = None
    last_completed_idx = None
    for idx, step in enumerate(current_plan.steps):
        if step.execution_res:
            last_completed_step = step
            last_completed_idx = idx
    
    if not last_completed_step:
        logger.warning("[VALIDATOR] No completed steps found, routing to research_team")
        return Command(goto="research_team")
    
    execution_res = last_completed_step.execution_res
    
    # Quick check for obvious errors
    execution_str = str(execution_res).lower()
    has_error_indicators = any(indicator in execution_str[:500] for indicator in [
        "[error]", "error:", "failed:", "exception:", 
        "traceback", "invalid", "uuid", "syntax error"
    ])
    
    # Use LLM to validate result for non-obvious cases
    try:
        validation_prompt = f"""Analyze if this step execution succeeded:

**Step Title:** {last_completed_step.title}
**Step Description:** {last_completed_step.description}

**Execution Result (first 1000 chars):**
{str(execution_res)[:1000]}

**Analysis Required:**
1. Did it achieve the intended goal?
2. Is the output valid and useful?
3. Are there any errors or critical issues?

**Respond with ONLY valid JSON:**
{{
    "status": "success" | "partial" | "failure",
    "reason": "brief explanation (max 100 chars)",
    "should_retry": true | false,
    "suggested_fix": "what to do differently (max 200 chars)"
}}

IMPORTANT: Your response must be ONLY the JSON object, no other text."""

        llm = get_llm_by_type("basic")
        validation_result = llm.invoke(validation_prompt)
        validation_content = validation_result.content.strip()
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', validation_content, re.DOTALL)
        if json_match:
            validation = json.loads(json_match.group(0))
        else:
            # Fallback if LLM didn't return JSON
            logger.warning("[VALIDATOR] LLM didn't return valid JSON, using heuristic")
            if has_error_indicators:
                validation = {
                    "status": "failure",
                    "reason": "Detected error indicators in execution result",
                    "should_retry": True,
                    "suggested_fix": "Fix the error and retry"
                }
            else:
                validation = {
                    "status": "success",
                    "reason": "No obvious errors detected",
                    "should_retry": False,
                    "suggested_fix": ""
                }
    
    except Exception as e:
        logger.error(f"[VALIDATOR] Error during validation: {e}", exc_info=True)
        # Default to success if validation fails
        validation = {
            "status": "success",
            "reason": "Validation failed, assuming success",
            "should_retry": False,
            "suggested_fix": ""
        }
    
    # Log validation result
    logger.info(f"[VALIDATOR] Step '{last_completed_step.title}' validation: {validation['status']} - {validation['reason']}")
    
    # Route based on validation
    validation_results = state.get("validation_results", [])
    validation_results.append({
        "step_index": last_completed_idx,
        "step_title": last_completed_step.title,
        **validation
    })
    
    if validation["status"] == "success":
        logger.info(f"[VALIDATOR] ✅ Step '{last_completed_step.title}' validated successfully")
        
        # CRITICAL: Check if all steps are now complete (double-check to prevent loops)
        all_steps_complete = all(step.execution_res for step in current_plan.steps)
        completed_count = sum(1 for step in current_plan.steps if step.execution_res)
        total_steps = len(current_plan.steps)
        
        logger.info(
            f"[VALIDATOR] 🔍 DEBUG: Step completion status - "
            f"Completed: {completed_count}/{total_steps}, "
            f"All complete: {all_steps_complete}"
        )
        
        if all_steps_complete:
            logger.info(f"[VALIDATOR] ✅ All {total_steps} steps completed and validated! Routing to reporter.")
            return Command(
                update={
                    "validation_results": validation_results,
                    "retry_count": 0  # Reset retry count on success
                },
                goto="reporter"
            )
        
        # Not all steps complete, continue to next step
        logger.info(f"[VALIDATOR] 🔄 Continuing to next step ({completed_count + 1}/{total_steps})")
        return Command(
            update={
                "validation_results": validation_results,
                "retry_count": 0  # Reset retry count on success
            },
            goto="research_team"
        )
    
    elif validation["status"] == "partial":
        logger.warning(f"[VALIDATOR] ⚠️ Step partially successful: {validation['reason']}")
        return Command(
            update={
                "validation_results": validation_results,
                "retry_count": 0  # Reset retry count on partial success
            },
            goto="research_team"
        )
    
    else:  # failure
        logger.error(f"[VALIDATOR] ❌ Step failed: {validation['reason']}")
        
        retry_count = state.get("retry_count", 0)
        max_retries = 2  # Max 2 retries before replanning
        plan_iterations = state.get("plan_iterations", 0)
        max_replan_iterations = state.get("max_replan_iterations", 3)
        
        # Check if should retry or replan
        if validation["should_retry"] and retry_count < max_retries:
            # Retry same step - clear execution_res to mark as incomplete
            logger.info(f"[VALIDATOR] 🔄 Retrying step (attempt {retry_count + 1}/{max_retries})")
            
            # Clear the failed step's execution_res so it gets retried
            from src.prompts.planner_model import Step, Plan
            updated_steps = list(current_plan.steps)
            updated_steps[last_completed_idx] = Step(
                need_search=last_completed_step.need_search,
                title=last_completed_step.title,
                description=last_completed_step.description,
                step_type=last_completed_step.step_type,
                execution_res=None  # Clear to retry
            )
            
            updated_plan = Plan(
                locale=current_plan.locale,
                has_enough_context=current_plan.has_enough_context,
                thought=current_plan.thought,
                title=current_plan.title,
                steps=updated_steps
            )
            
            return Command(
                update={
                    "retry_count": retry_count + 1,
                    "validation_results": validation_results,
                    "current_plan": updated_plan,
                    "current_step_index": last_completed_idx  # Go back to retry
                },
                goto="research_team"
            )
        
        elif plan_iterations < max_replan_iterations:
            # Need to replan - route to reflection
            logger.warning(f"[VALIDATOR] 🤔 Routing to reflector for replanning (iteration {plan_iterations + 1}/{max_replan_iterations})")
            logger.warning(f"[VALIDATOR] Failure reason: {validation.get('reason', 'Unknown')}")
            logger.warning(f"[VALIDATOR] Suggested fix: {validation.get('suggested_fix', 'None')}")
            
            # NOTE: Don't update retry_count here - let reflection_node handle it to avoid state conflicts
            return Command(
                update={
                    "validation_results": validation_results,
                    "replan_reason": validation["reason"],
                    # retry_count will be reset by reflection_node
                },
                goto="reflector"
            )
        else:
            # Max replanning iterations reached, continue anyway
            logger.error(f"[VALIDATOR] ⚠️ Max replan iterations reached ({plan_iterations}/{max_replan_iterations}), continuing to reporter")
            logger.error(f"[VALIDATOR] Final failure reason: {validation.get('reason', 'Unknown')}")
            return Command(
                update={
                    "validation_results": validation_results
                },
                goto="reporter"
            )


def reflection_node(state: State, config: RunnableConfig) -> Command:
    """
    Reflects on failed execution and provides context for replanning.
    
    Analyzes what went wrong, why it failed, and suggests alternative approaches.
    Routes back to planner with reflection context.
    """
    logger.info("[REFLECTION] Analyzing failure and preparing for replan")
    
    current_plan = state.get("current_plan")
    validation_results = state.get("validation_results", [])
    replan_reason = state.get("replan_reason", "Unknown failure")
    plan_iterations = state.get("plan_iterations", 0)
    
    if not current_plan or isinstance(current_plan, str):
        logger.error("[REFLECTION] No valid plan to reflect on, routing to planner")
        return Command(
            update={"plan_iterations": plan_iterations + 1},
            goto="planner"
        )
    
    # Build reflection context
    steps_summary = []
    for idx, step in enumerate(current_plan.steps):
        step_info = {
            "index": idx + 1,
            "title": step.title,
            "status": "completed" if step.execution_res else "pending"
        }
        if step.execution_res:
            # Include first 300 chars of result
            result_preview = str(step.execution_res)[:300]
            step_info["result_preview"] = result_preview
        steps_summary.append(step_info)
    
    # Get failed validations
    failed_validations = [v for v in validation_results if v.get("status") == "failure"]
    
    reflection_prompt = f"""Reflect on why the current plan failed and suggest a better approach.

**Original Plan:** {current_plan.title}
**Plan Thought:** {current_plan.thought}

**Steps Executed:**
{json.dumps(steps_summary, indent=2)}

**Failed Validations:**
{json.dumps(failed_validations, indent=2)}

**Primary Failure Reason:** {replan_reason}

**Reflection Task:**
1. Identify the root cause of failure
2. Explain why the current approach didn't work
3. Suggest a specific alternative approach
4. Identify any missing information needed

**CRITICAL:** If the failure is due to using the wrong sprint number (e.g., Sprint 8 instead of Sprint 10), 
you MUST suggest explicitly looking up the sprint by NAME/NUMBER in the list_sprints results, 
not by index position. The new plan should include clear instructions to:
- Call list_sprints() first
- Search the results for the specific sprint number/name (e.g., "Sprint 10")
- Extract the correct sprint_id (UUID) from the matching sprint
- Use that exact sprint_id in all subsequent calls

**Provide a concise reflection (max 500 words) that will help create a better plan.**
"""
    
    try:
        llm = get_llm_by_type("basic")
        reflection_result = llm.invoke(reflection_prompt)
        reflection_content = reflection_result.content
        
        logger.info(f"[REFLECTION] Generated reflection ({len(reflection_content)} chars)")
        logger.debug(f"[REFLECTION] Content preview: {reflection_content[:200]}...")
        
    except Exception as e:
        logger.error(f"[REFLECTION] Error generating reflection: {e}", exc_info=True)
        reflection_content = f"Failed to generate detailed reflection. Reason: {replan_reason}. Suggested: Try a different approach or break into smaller steps."
    
    # Route back to planner with reflection context
    return Command(
        update={
            "reflection": reflection_content,
            "plan_iterations": plan_iterations + 1,
            "retry_count": 0  # Reset retry count for new plan
        },
        goto="planner"
    )


async def react_agent_node(
    state: State, config: RunnableConfig
) -> Command[Literal["planner", "reporter"]]:
    """
    Fast ReAct agent for simple queries with auto-escalation.
    
    Uses ReAct pattern (Reasoning + Acting) for quick execution.
    Automatically escalates to full pipeline if:
    - Too many iterations (>8)
    - Repeated errors (>2)
    - Agent explicitly requests planning
    
    This is the optimistic fast path for 80% of queries.
    """
    logger.info("[REACT-AGENT] 🚀 Starting fast ReAct agent")
    
    configurable = Configuration.from_runnable_config(config)
    
    # Load PM tools + web_search for background investigation
    try:
        from src.tools.pm_tools import get_pm_tools
        from src.tools.search import get_web_search_tool
        from src.utils.json_utils import sanitize_tool_response
        from langchain_core.tools import BaseTool
        
        # Get PM tools (synchronous function, no config needed)
        pm_tools = get_pm_tools()
        
        # Add web search tool for background investigation when needed
        search_tool = get_web_search_tool(
            configurable.max_search_results,
            provider_id=configurable.search_provider
        )
        
        # CRITICAL FIX: Wrap all tools to truncate large outputs before they enter the scratchpad
        # This prevents 329K token accumulation in the agent's scratchpad
        import asyncio
        import inspect
        
        def wrap_tool_with_truncation(tool: BaseTool, max_tokens: int = 1000) -> BaseTool:
            """Wrap a tool to truncate its output and track usage in Cursor-style tracker.
            
            CRITICAL: Using 1000 tokens (4000 chars) per tool result to prevent accumulation.
            Even with 3 iterations, max accumulation = 3K tokens, which is safe.
            
            Also tracks usage in Cursor-style context tracker for auto-optimization.
            """
            from src.utils.cursor_style_context_tracker import get_global_tracker
            
            # Check if tool has func attribute (for @tool decorated functions)
            if hasattr(tool, 'func'):
                original_func = tool.func
                is_async = inspect.iscoroutinefunction(original_func)
                
                if is_async:
                    async def truncated_func(*args, **kwargs):
                        result = await original_func(*args, **kwargs)
                        result_str = str(result)
                        max_chars = max_tokens * 4  # 1000 tokens = 4000 chars
                        original_len = len(result_str)
                        
                        # Estimate tokens (rough: 4 chars per token)
                        estimated_tokens = original_len // 4
                        
                        # Track usage in Cursor-style tracker
                        tracker = get_global_tracker()
                        if tracker:
                            tool_name = f"tool_{tool.name}"
                            needs_optimize, reason = tracker.record_usage(tool_name, estimated_tokens)
                            if needs_optimize:
                                logger.debug(
                                    f"[REACT-AGENT] 🔍 Tool '{tool.name}' usage triggered optimization check: {reason}"
                                )
                        
                        if original_len > max_chars:
                            logger.warning(
                                f"[REACT-AGENT] 🔍 Tool '{tool.name}' returned {original_len:,} chars "
                                f"(≈{estimated_tokens:,} tokens). Truncating to {max_chars:,} chars (≈{max_tokens:,} tokens)."
                            )
                            result_str = sanitize_tool_response(result_str, max_length=max_chars, compress_arrays=True)
                            final_len = len(result_str)
                            logger.info(
                                f"[REACT-AGENT] ✅ Tool '{tool.name}' truncated: {original_len:,} → {final_len:,} chars "
                                f"(≈{estimated_tokens:,} → ≈{final_len//4:,} tokens)"
                            )
                        else:
                            logger.debug(f"[REACT-AGENT] Tool '{tool.name}' returned {original_len:,} chars (within limit)")
                        return result_str
                    tool.func = truncated_func
                else:
                    def truncated_func(*args, **kwargs):
                        from src.utils.cursor_style_context_tracker import get_global_tracker
                        result = original_func(*args, **kwargs)
                        result_str = str(result)
                        max_chars = max_tokens * 4  # 1000 tokens = 4000 chars
                        original_len = len(result_str)
                        estimated_tokens = original_len // 4
                        
                        # Track usage in Cursor-style tracker
                        tracker = get_global_tracker()
                        if tracker:
                            tool_name = f"tool_{tool.name}"
                            tracker.record_usage(tool_name, estimated_tokens)
                        
                        if original_len > max_chars:
                            logger.warning(
                                f"[REACT-AGENT] 🔍 Tool '{tool.name}' returned {original_len:,} chars "
                                f"(≈{original_len//4:,} tokens). Truncating to {max_chars:,} chars (≈{max_tokens:,} tokens)."
                            )
                            result_str = sanitize_tool_response(result_str, max_length=max_chars, compress_arrays=True)
                            final_len = len(result_str)
                            logger.info(
                                f"[REACT-AGENT] ✅ Tool '{tool.name}' truncated: {original_len:,} → {final_len:,} chars "
                                f"(≈{original_len//4:,} → ≈{final_len//4:,} tokens)"
                            )
                        else:
                            logger.debug(f"[REACT-AGENT] Tool '{tool.name}' returned {original_len:,} chars (within limit)")
                        return result_str
                    tool.func = truncated_func
            # Check if tool has _arun method (for BaseTool subclasses)
            elif hasattr(tool, '_arun'):
                original_arun = tool._arun
                async def truncated_arun(*args, **kwargs):
                    from src.utils.cursor_style_context_tracker import get_global_tracker
                    result = await original_arun(*args, **kwargs)
                    result_str = str(result)
                    max_chars = max_tokens * 4  # 1000 tokens = 4000 chars
                    original_len = len(result_str)
                    estimated_tokens = original_len // 4
                    
                    # Track usage in Cursor-style tracker
                    tracker = get_global_tracker()
                    if tracker:
                        tool_name = f"tool_{tool.name}"
                        tracker.record_usage(tool_name, estimated_tokens)
                    
                    if original_len > max_chars:
                        logger.warning(
                            f"[REACT-AGENT] 🔍 Tool '{tool.name}' returned {original_len:,} chars "
                            f"(≈{original_len//4:,} tokens). Truncating to {max_chars:,} chars (≈{max_tokens:,} tokens)."
                        )
                        result_str = sanitize_tool_response(result_str, max_length=max_chars, compress_arrays=True)
                        final_len = len(result_str)
                        logger.info(
                            f"[REACT-AGENT] ✅ Tool '{tool.name}' truncated: {original_len:,} → {final_len:,} chars "
                            f"(≈{original_len//4:,} → ≈{final_len//4:,} tokens)"
                        )
                    else:
                        logger.debug(f"[REACT-AGENT] Tool '{tool.name}' returned {original_len:,} chars (within limit)")
                    return result_str
                tool._arun = truncated_arun
            # Check if tool has _run method (for BaseTool subclasses)
            elif hasattr(tool, '_run'):
                original_run = tool._run
                def truncated_run(*args, **kwargs):
                    from src.utils.cursor_style_context_tracker import get_global_tracker
                    result = original_run(*args, **kwargs)
                    result_str = str(result)
                    max_chars = max_tokens * 4  # 1000 tokens = 4000 chars
                    original_len = len(result_str)
                    estimated_tokens = original_len // 4
                    
                    # Track usage in Cursor-style tracker
                    tracker = get_global_tracker()
                    if tracker:
                        tool_name = f"tool_{tool.name}"
                        tracker.record_usage(tool_name, estimated_tokens)
                    
                    if original_len > max_chars:
                        logger.warning(
                            f"[REACT-AGENT] 🔍 Tool '{tool.name}' returned {original_len:,} chars "
                            f"(≈{original_len//4:,} tokens). Truncating to {max_chars:,} chars (≈{max_tokens:,} tokens)."
                        )
                        result_str = sanitize_tool_response(result_str, max_length=max_chars, compress_arrays=True)
                        final_len = len(result_str)
                        logger.info(
                            f"[REACT-AGENT] ✅ Tool '{tool.name}' truncated: {original_len:,} → {final_len:,} chars "
                            f"(≈{original_len//4:,} → ≈{final_len//4:,} tokens)"
                        )
                    else:
                        logger.debug(f"[REACT-AGENT] Tool '{tool.name}' returned {original_len:,} chars (within limit)")
                    return result_str
                tool._run = truncated_run
            else:
                logger.warning(f"[REACT-AGENT] ⚠️ Tool '{tool.name}' has no func/_run/_arun attribute. Cannot wrap for truncation.")
            
            return tool
        
        # Wrap all tools to truncate outputs - VERY AGGRESSIVE: 1000 tokens per tool (was 2000)
        # This prevents scratchpad from accumulating too many tokens
        # With 3 max iterations, max accumulation = 3K tokens, which is safe
        wrapped_pm_tools = [wrap_tool_with_truncation(tool, max_tokens=1000) for tool in pm_tools]
        wrapped_search_tool = wrap_tool_with_truncation(search_tool, max_tokens=1000)
        
        tools = wrapped_pm_tools + [wrapped_search_tool]
        logger.info(f"[REACT-AGENT] Loaded {len(pm_tools)} PM tools + web_search (all wrapped with truncation)")
    except Exception as e:
        logger.error(f"[REACT-AGENT] Failed to load tools: {e}", exc_info=True)
        # Escalate if tools fail
        return Command(
            update={"escalation_reason": "tool_loading_failed"},
            goto="planner"
        )
    
    # Get user query
    user_query = state.get("research_topic") or get_message_content(state["messages"][-1])
    project_id = state.get("project_id", "")
    
    logger.info(f"[REACT-AGENT] Query: {user_query[:100]}...")
    logger.info(f"[REACT-AGENT] Project ID: {project_id}")
    logger.info(f"[REACT-AGENT] Available tools: {len(tools)}")
    
    # CRITICAL: Apply ADAPTIVE context compression (based on model's context window)
    # ReAct was trying to send 331K tokens! Need to compress conversation history
    from src.utils.adaptive_context_config import get_adaptive_context_manager
    from src.llms.llm import get_llm_token_limit_by_type
    
    # Extract frontend history for token budgeting
    frontend_count = state.get("frontend_history_message_count", 0)
    all_messages = list(state.get("messages", []))
    frontend_messages = all_messages[:frontend_count] if frontend_count > 0 else []
    
    # Get model's context limit
    model_context_limit = get_llm_token_limit_by_type("basic") or 16385
    
    # Get adaptive context manager (uses 35% of model's context for ReAct)
    logger.info(
        f"[REACT-AGENT] 🔍 DEBUG: Creating context manager - "
        f"agent_type=react_agent, "
        f"model_context_limit={model_context_limit:,}, "
        f"frontend_messages={len(frontend_messages)}"
    )
    context_manager = get_adaptive_context_manager(
        agent_type="react_agent",
        model_name="gpt-3.5-turbo",  # Will be replaced by actual model
        model_context_limit=model_context_limit,
        frontend_history_messages=frontend_messages
    )
    logger.info(
        f"[REACT-AGENT] 🔍 DEBUG: Context manager created - "
        f"token_limit={context_manager.token_limit}, "
        f"compression_mode={context_manager.compression_mode}, "
        f"preserve_prefix={context_manager.preserve_prefix_message_count}"
    )
    
    # Get actual model name early (needed for token counting before compression)
    from langgraph.prebuilt import create_react_agent
    llm = get_llm_by_type("basic")
    
    # Try to get model name from LLM instance (do this early so it's available for context compression)
    try:
        actual_model_name = getattr(llm, 'model_name', None) or getattr(llm, 'model', None) or "gpt-3.5-turbo"
    except:
        actual_model_name = "gpt-3.5-turbo"
    
    logger.info(f"[REACT-AGENT] 🔍 DEBUG: Model name determined: {actual_model_name}")
    
    # Compress the state to fit in ReAct's budget
    # ReAct only needs: current query + recent context (not full history)
    logger.info(f"[REACT-AGENT] 🔍 DEBUG: Starting context compression. Original messages: {len(all_messages)}")
    logger.info(f"[REACT-AGENT] 🔍 DEBUG: ContextManager token_limit: {context_manager.token_limit}")
    logger.info(f"[REACT-AGENT] 🔍 DEBUG: ContextManager compression_mode: {context_manager.compression_mode}")
    logger.info(f"[REACT-AGENT] 🔍 DEBUG: ContextManager agent_type: {context_manager.agent_type}")
    logger.info(f"[REACT-AGENT] 🔍 DEBUG: State type: {type(state)}, has 'messages' key: {'messages' in state if isinstance(state, dict) else 'N/A'}")
    
    # Count tokens BEFORE compression to see if we're over limit
    try:
        pre_compression_tokens = context_manager.count_tokens(all_messages, model=actual_model_name)
        is_over = context_manager.is_over_limit(all_messages)
        logger.info(
            f"[REACT-AGENT] 🔍 DEBUG: BEFORE compression - "
            f"Token count: {pre_compression_tokens:,}, "
            f"Token limit: {context_manager.token_limit:,}, "
            f"Is over limit: {is_over}"
        )
    except Exception as e:
        logger.warning(f"[REACT-AGENT] 🔍 DEBUG: Failed to count tokens before compression: {e}")
    
    compressed_state = context_manager.compress_messages(state)
    
    # Extract compressed messages (CRITICAL FIX: Actually use the compressed state!)
    compressed_messages = compressed_state.get("messages", [])
    optimization_metadata = compressed_state.get("_context_optimization")
    
    logger.info(
        f"[REACT-AGENT] 🔍 DEBUG: Context compression complete. "
        f"Original: {len(all_messages)} messages, "
        f"Compressed: {len(compressed_messages)} messages"
    )
    logger.info(f"[REACT-AGENT] 🔍 DEBUG: Optimization metadata: {optimization_metadata}")
    if optimization_metadata:
        logger.info(
            f"[REACT-AGENT] 🔍 DEBUG: Compression details - "
            f"Compressed: {optimization_metadata.get('compressed', False)}, "
            f"Original tokens: {optimization_metadata.get('original_tokens', 0):,}, "
            f"Compressed tokens: {optimization_metadata.get('compressed_tokens', 0):,}, "
            f"Ratio: {optimization_metadata.get('compression_ratio', 1.0):.2%}, "
            f"Strategy: {optimization_metadata.get('strategy', 'unknown')}"
        )
    else:
        logger.error(f"[REACT-AGENT] 🚨 CRITICAL: No optimization metadata returned! This means compression didn't work!")
    
    logger.info(f"[REACT-AGENT] 🔍 DEBUG: Using model: {actual_model_name}, Model limit: {model_context_limit:,} tokens")
    
    # Count tokens in compressed messages
    compressed_token_count = context_manager.count_tokens(compressed_messages, model=actual_model_name)
    original_token_count = context_manager.count_tokens(all_messages, model=actual_model_name)
    
    logger.info(
        f"[REACT-AGENT] 🔍 DEBUG: Token counts - "
        f"Original: {original_token_count:,} tokens, "
        f"Compressed: {compressed_token_count:,} tokens, "
        f"Model limit: {model_context_limit:,} tokens, "
        f"ReAct budget (35%): {int(model_context_limit * 0.35):,} tokens"
    )
    
    # Estimate total tokens that will be sent to LLM
    # ReAct agent sends: system prompt + tool descriptions + query + agent scratchpad
    # Estimate: prompt (~2K) + tools (~5K) + query (~100) + scratchpad (~1K) = ~8K base
    estimated_prompt_tokens = 2000  # System prompt
    estimated_tool_tokens = len(tools) * 200  # ~200 tokens per tool description
    estimated_query_tokens = len(user_query) // 4  # Rough estimate
    estimated_base_tokens = estimated_prompt_tokens + estimated_tool_tokens + estimated_query_tokens + 1000  # Buffer
    
    # IMPORTANT: LangChain's ReAct agent is stateless - it doesn't use chat history in the prompt
    # However, we still check if the compressed messages would fit if they were included
    # This is a safety check in case the LLM somehow accesses the full state
    total_estimated_tokens = estimated_base_tokens + compressed_token_count
    
    logger.info(
        f"[REACT-AGENT] 🔍 DEBUG: Token estimation - "
        f"Base (prompt+tools+query): ~{estimated_base_tokens:,} tokens, "
        f"With compressed messages: ~{total_estimated_tokens:,} tokens, "
        f"Model limit: {model_context_limit:,} tokens"
    )
    
    # PRE-FLIGHT CHECK: Check against both context limit AND TPM rate limit
    # TPM (Tokens Per Minute) limits are often lower than context limits
    # For gpt-3.5-turbo: Context limit = 16,385, TPM limit = 200,000
    # For gpt-4o-mini: Context limit = 128,000, TPM limit = 2,000,000
    # We need to be conservative because tool results accumulate in scratchpad
    
    # Get TPM limit based on model (default to 200K for gpt-3.5-turbo)
    tpm_limit = 200000  # Default TPM limit
    if "gpt-4o" in actual_model_name.lower() or "gpt-4" in actual_model_name.lower():
        tpm_limit = 2000000  # GPT-4 models have higher TPM
    elif "gpt-3.5" in actual_model_name.lower():
        tpm_limit = 200000  # GPT-3.5-turbo TPM limit
    
    # Use the MORE restrictive limit (context or TPM)
    effective_limit = min(model_context_limit, tpm_limit)
    
    # INTELLIGENT PRE-FLIGHT CHECK:
    # 1. If base tokens (without tool accumulation) are already > 80% of limit, escalate
    # 2. If base tokens + realistic tool accumulation > limit, escalate
    # 3. Don't use overly conservative 30% threshold - that's too aggressive
    
    # Realistic tool accumulation: 3 iterations * 1000 tokens = 3K tokens (no 2x safety factor)
    # Tool truncation limits each tool result to 1000 tokens max
    realistic_tool_accumulation = 3 * 1000  # 3K tokens (realistic max with truncation)
    
    # Check 1: Base tokens already too high?
    base_token_threshold = int(effective_limit * 0.80)  # 80% of limit
    if total_estimated_tokens > base_token_threshold:
        logger.warning(
            f"[REACT-AGENT] ⚠️ PRE-FLIGHT CHECK FAILED: "
            f"Base estimated tokens ({total_estimated_tokens:,}) exceed 80% of limit ({base_token_threshold:,}). "
            f"Escalating to planner."
        )
        return Command(
            update={
                "escalation_reason": f"token_limit_exceeded_base: estimated={total_estimated_tokens}, threshold={base_token_threshold}, limit={effective_limit}",
                "partial_result": f"Context too large ({total_estimated_tokens:,} tokens estimated, limit: {effective_limit:,}). Escalating to full pipeline.",
                "goto": "planner"
            },
            goto="planner"
        )
    
    # Check 2: Base + realistic tool accumulation > limit?
    total_with_realistic_tools = total_estimated_tokens + realistic_tool_accumulation
    if total_with_realistic_tools > effective_limit:
        logger.warning(
            f"[REACT-AGENT] ⚠️ PRE-FLIGHT CHECK FAILED: "
            f"Estimated tokens ({total_estimated_tokens:,}) + realistic tool accumulation ({realistic_tool_accumulation:,}) = {total_with_realistic_tools:,} "
            f"exceeds effective limit ({effective_limit:,}). "
            f"Escalating to planner."
        )
        return Command(
            update={
                "escalation_reason": f"token_limit_exceeded_with_tools: estimated={total_estimated_tokens}, with_tools={total_with_realistic_tools}, limit={effective_limit}",
                "partial_result": f"Context too large ({total_estimated_tokens:,} tokens estimated, with tool accumulation: {total_with_realistic_tools:,}). Escalating to full pipeline.",
                "goto": "planner"
            },
            goto="planner"
        )
    
    logger.info(
        f"[REACT-AGENT] ✅ PRE-FLIGHT CHECK PASSED: "
        f"Base tokens ({total_estimated_tokens:,}) < 80% threshold ({base_token_threshold:,}), "
        f"and with realistic tool accumulation ({total_with_realistic_tools:,}) < limit ({effective_limit:,})"
    )
    
    # Create context optimization tool call messages
    optimization_messages = []
    if optimization_metadata:
        optimization_messages = _add_context_optimization_tool_call(state, "react_agent", optimization_metadata)
        logger.info(f"[REACT-AGENT] 🔍 DEBUG: Created {len(optimization_messages)} optimization messages")
    
    logger.info(f"[REACT-AGENT] 🔍 DEBUG: Created LLM instance: {type(llm).__name__}")
    
    # ReAct prompt - ENHANCED with explicit tool name format and project_id context
    project_id_context = ""
    if project_id:
        project_id_context = f"""

**🚨 CRITICAL: PROJECT ID IS ALREADY PROVIDED**
- **Project ID:** {project_id}
- **DO NOT call `list_projects`** - the project is already identified!
- **If you need project details:** Use `get_project` with project_id: {project_id}
- **For sprint/task queries:** Use the project_id directly in tool calls (e.g., `list_sprints` with project_id)
- **Only call `list_projects`** if the user explicitly asks to list/search all projects by name
- **For "analyse sprint X" queries:** Use the provided project_id directly - no need to search for projects!
"""
    
    react_prompt_template = """You are a helpful PM assistant with access to project management tools and web search.

**CRITICAL: You MUST include your reasoning in the message content BEFORE calling tools!**

Even when using structured tool calls, you MUST write your thinking process in the message content. This helps users understand your reasoning.

**WORKFLOW:**
1. **Understand the Request**: Read the user's question carefully
2. **Research if Needed**: If you're unsure how to fulfill the request, use `web_search` to research:
   - Best practices for the task
   - How to interpret or analyze the data
   - Industry standards or methodologies
   - Any context that would help you provide a better answer
3. **Plan Your Approach**: Think about which tools to use and in what order
4. **Execute**: Call the appropriate tools to get the data
5. **Analyze & Answer**: Process the data and provide a comprehensive answer

**CRITICAL: Tool Name Format**
- Tool names do NOT have parentheses: use `list_sprints` NOT `list_sprints()`
- Tool names do NOT have parentheses: use `get_sprint` NOT `get_sprint()`
- Tool names do NOT have parentheses: use `list_projects` NOT `list_projects()`
- Always use the EXACT tool name as shown in the "Available tools" section below

**MESSAGE FORMAT (CRITICAL - Include reasoning in content!):**

When you want to call a tool, your message should look like this:

**Content (REQUIRED - write your thinking here):**
```
Thought: [Your reasoning about what you need to do]
- What is the user asking for?
- What information do I need?
- Which tools should I use?
- Do I need to research first (use web_search)?
- What's my plan?
```

**Then call the tool** (structured tool call will be added automatically)

**Example Flow:**

**ITERATION 1 - Research (if needed):**
Content: "The user wants to analyze Sprint 4. I should first understand what makes a good sprint analysis. Let me research best practices for sprint analysis to ensure I provide comprehensive insights."
Tool: web_search
Tool Input: {{"{{"query": "sprint analysis best practices agile methodology"}}}}

**ITERATION 2 - Get Data:**
Content: "Based on the research, a good sprint analysis should include velocity, burndown, completed work, and blockers. Now I need to get the sprint data. I have the project_id, so I'll call list_sprints to find Sprint 4's ID."
Tool: list_sprints
Tool Input: {{"{{"project_id": "d7e300c6-d6c0-4c08-bc8d-e41967458d86:478"}}}}

**ITERATION 3 - Analyze:**
Content: "I found Sprint 4 with ID '613'. Now I'll get the detailed sprint report to analyze velocity, completed tasks, and performance metrics."
Tool: sprint_report
Tool Input: {{"{{"sprint_id": "613", "project_id": "d7e300c6-d6c0-4c08-bc8d-e41967458d86:478"}}}}

**ITERATION 4 - Final Answer:**
Content: "Based on the sprint report and best practices I researched, here's my analysis: [comprehensive analysis with insights]"

**EXAMPLES OF CORRECT TOOL CALLS:**

✅ CORRECT - When project_id is provided (USE IT DIRECTLY, don't call list_projects):
Action: list_sprints
Action Input: {{"{{"project_id": "d7e300c6-d6c0-4c08-bc8d-e41967458d86:495"}}}}
(Use the project_id from context - see "CURRENT PROJECT ID" section above)

✅ CORRECT - Complete Sprint Analysis Workflow (STEP-BY-STEP):

**Example: User asks "Analyze Sprint 4" with project_id already provided**

**ITERATION 1:**
Thought: The user wants to analyze Sprint 4. I have the project_id (d7e300c6-d6c0-4c08-bc8d-e41967458d86:478) already, so I should call list_sprints to get all sprints and find Sprint 4's ID.
Action: list_sprints
Action Input: {{"{{"project_id": "d7e300c6-d6c0-4c08-bc8d-e41967458d86:478"}}}}

**ITERATION 2:**
Observation: {{"success": true, "sprints": [{{"id": "617", "name": "Sprint 8", "status": "future"}}, {{"id": "616", "name": "Sprint 7", "status": "future"}}, {{"id": "615", "name": "Sprint 6", "status": "future"}}, {{"id": "614", "name": "Sprint 5", "status": "active"}}, {{"id": "613", "name": "Sprint 4", "status": "closed"}}, {{"id": "612", "name": "Sprint 3", "status": "closed"}}, ...], "count": 10}}

Thought: I received the list_sprints response. I can see it's a JSON object with a "sprints" array. I need to find the sprint with name "Sprint 4". Looking at the sprints array, I can see:
- Sprint with id "617" has name "Sprint 8"
- Sprint with id "616" has name "Sprint 7"
- Sprint with id "615" has name "Sprint 6"
- Sprint with id "614" has name "Sprint 5"
- Sprint with id "613" has name "Sprint 4" ← THIS IS THE ONE!
- Sprint with id "612" has name "Sprint 3"

So Sprint 4 has id "613". Now I should call sprint_report with sprint_id="613" and the project_id.
Action: sprint_report
Action Input: {{"{{"sprint_id": "613", "project_id": "d7e300c6-d6c0-4c08-bc8d-e41967458d86:478"}}}}

**ITERATION 3:**
Observation: [Sprint report data will be shown here]

Thought: I now have the sprint report for Sprint 4. I have enough information to provide a comprehensive analysis.
Final Answer: [Provide the analysis based on the sprint report data]

**KEY POINTS:**
1. **ALWAYS parse the JSON response** - The list_sprints response is JSON, not plain text
2. **Search the sprints array** - Look through each sprint object in the "sprints" array
3. **Match by name field** - Find the sprint where `name == "Sprint 4"` or name contains "4"
4. **Extract the id field** - Once you find the matching sprint, use its "id" field value (e.g., "613")
5. **Use the actual ID** - NEVER use "Sprint 4" or "Sprint 4 ID" as the sprint_id - use the actual ID like "613"

✅ CORRECT - Get project details when project_id is provided:
Action: get_project
Action Input: {{"{{"project_id": "d7e300c6-d6c0-4c08-bc8d-e41967458d86:495"}}}}
(Use get_project to get project name/details if needed, NOT list_projects)

✅ CORRECT - Sprint report with provided project_id:
Action: sprint_report
Action Input: {{"{{"sprint_id": "e6890ea6-0c3c-4a83-aa05-41b223df3284", "project_id": "d7e300c6-d6c0-4c08-bc8d-e41967458d86:495"}}}}

✅ CORRECT - Only when project_id is NOT provided and you need to search by name:
Action: list_projects
Action Input: {{"{{"}}}}
(Only use this if you need to search for a project by name)

❌ WRONG - Calling list_projects when project_id is already provided:
Action: list_projects
Action Input: {{"{{"}}}}
(If project_id is provided in context, use it directly - don't call list_projects!)

❌ WRONG (has parentheses):
Action: list_sprints()
Action Input: {{"{{"project_id": "project_id"}}}}

❌ WRONG (placeholder values):
Action: list_sprints
Action Input: {{"{{"project_id": "project_id"}}}}

CRITICAL WORKFLOW RULES:
1. **Tool Name Format (CRITICAL!):**
   - Tool names are WITHOUT parentheses: `list_sprints`, `get_sprint`, `list_projects`
   - ❌ NEVER use: `list_sprints()`, `get_sprint()`, `list_projects()`
   - ✅ ALWAYS use: `list_sprints`, `get_sprint`, `list_projects`
   - Check the "Available tools" section for exact tool names

**⚠️ CRITICAL: COMPRESSED RESULTS - DO NOT RETRY!**
- Tool results may be compressed/truncated to fit token limits
- If you see "[NOTE: Result was intelligently compressed..." in a tool response, this is NORMAL
- **For `list_projects`**: Even when compressed, ALL project IDs and names are preserved - you can search through all projects
- **For `list_sprints`**: Even when compressed, ALL sprint IDs, names, and status are preserved - you can search through all sprints to find "Sprint 4", "Sprint 10", etc.
- **For other tools**: Compressed results contain summaries or samples, but are still COMPLETE for the task
- The compressed result IS COMPLETE - use the provided data as-is
- ❌ DO NOT retry the same tool call expecting different/more results
- ❌ DO NOT assume compressed results are incomplete or errors
- ✅ Search through the provided data - if you don't find what you need, it doesn't exist (don't retry)

2. **Project ID Usage (CRITICAL!):**
   - **IF PROJECT_ID IS PROVIDED IN CONTEXT:**
     - ✅ **USE IT DIRECTLY** - do NOT call `list_projects`
     - ✅ Use `get_project(project_id)` if you need project details (name, description, etc.)
     - ✅ Use the project_id directly in other tools (e.g., `list_sprints(project_id)`)
     - ❌ **DO NOT call `list_projects`** - it's unnecessary and wastes tokens
   - **IF PROJECT_ID IS NOT PROVIDED:**
     - If user mentions a project NAME (e.g., "HD Saison"), call `list_projects` to search
     - Search through the projects array for the project name (case-insensitive)
     - Extract the actual project_id (UUID format) from the matching project
     - If you don't find the project, it doesn't exist - don't retry `list_projects`
   - ❌ NEVER use placeholder strings like "project_id" or "sprint_id"
   - ✅ ALWAYS use actual UUIDs from tool results

3. **Sprint Analysis Workflow (CRITICAL - FOLLOW EXACTLY):**
   - **IF PROJECT_ID IS PROVIDED:**
     - ✅ Skip Step 1 - use the provided project_id directly
     - **ITERATION 1: Call list_sprints**
       - Thought: "I need to find Sprint 4's ID. I'll call list_sprints with the provided project_id."
       - Action: list_sprints
       - Action Input: {{"{{"project_id": "d7e300c6-d6c0-4c08-bc8d-e41967458d86:478"}}}}
     - **ITERATION 3: Parse JSON and Extract sprint_id**
       - Observation: You will receive a JSON response like:
         ```json
         {
           "success": true,
           "sprints": [
             {"id": "617", "name": "Sprint 8", "status": "future"},
             {"id": "616", "name": "Sprint 7", "status": "future"},
             {"id": "615", "name": "Sprint 6", "status": "future"},
             {"id": "614", "name": "Sprint 5", "status": "active"},
             {"id": "613", "name": "Sprint 4", "status": "closed"},  ← FIND THIS ONE!
             {"id": "612", "name": "Sprint 3", "status": "closed"},
             ...
           ],
           "count": 10
         }
         ```
       - Content: "I received the JSON response. I need to:
         1. Parse the JSON to access the 'sprints' array
         2. Search through each sprint object in the array
         3. Find the sprint where name == 'Sprint 4' or name contains '4'
         4. Extract the 'id' field from that sprint object
         
         Looking at the sprints array:
         - Sprint with id '617' has name 'Sprint 8' (not Sprint 4)
         - Sprint with id '616' has name 'Sprint 7' (not Sprint 4)
         - Sprint with id '615' has name 'Sprint 6' (not Sprint 4)
         - Sprint with id '614' has name 'Sprint 5' (not Sprint 4)
         - Sprint with id '613' has name 'Sprint 4' ← FOUND IT! The sprint_id is '613'
         - Sprint with id '612' has name 'Sprint 3' (not Sprint 4)
         
         So Sprint 4 has id '613'. Now I'll call sprint_report with sprint_id='613'."
       - Tool: sprint_report
       - Tool Input: {{"{{"sprint_id": "613", "project_id": "d7e300c6-d6c0-4c08-bc8d-e41967458d86:478"}}}}
     - **ITERATION 4: Provide Final Answer**
       - Observation: [Sprint report data]
       - Content: "I now have the sprint report for Sprint 4 and the research on best practices. I'll combine the research insights with the actual sprint data to provide a comprehensive analysis covering velocity, burndown, completed work, blockers, and team performance."
       - Final Answer: [Your comprehensive analysis combining research insights with sprint data]
   - **IF PROJECT_ID IS NOT PROVIDED:**
     - Step 1: Call `list_projects` to find project_id (only if needed)
     - Step 2-3: Same as above
   - **CRITICAL RULES:**
     - ❌ NEVER pass sprint names like "Sprint 4" directly to sprint_report!
     - ❌ NEVER use placeholder values like "sprint_id" or "Sprint 4 ID"!
     - ❌ NEVER retry list_sprints if you already got the response - the data is there, just parse it!
     - ✅ ALWAYS parse the JSON response (it's JSON, not plain text!)
     - ✅ ALWAYS search through the sprints array to find the matching sprint
     - ✅ ALWAYS extract the actual `id` field value (e.g., "613") from the sprint object
     - ✅ ALWAYS use the extracted ID in subsequent tool calls
     - ✅ **REMEMBER**: Even if `list_sprints` result is compressed, ALL sprint IDs and names are preserved - you can search through all sprints
     - ✅ **JSON STRUCTURE**: The response is `{{"success": true, "sprints": [{{"id": "...", "name": "...", ...}}, ...], "count": N}}`
     - ✅ **PARSING STEPS**: 1) Parse JSON → 2) Access "sprints" array → 3) Loop through sprints → 4) Match by name → 5) Extract id field

4. **Tool Input Format:**
   - Use VALID JSON in Action Input
   - Use actual UUIDs from tool results, NOT placeholder strings
   - Example: {{"{{"project_id": "d7e300c6-d6c0-4c08-bc8d-e41967458d86:478"}}}}
   - ❌ BAD: {{"{{"project_id": "project_id"}}}} (placeholder!)
   - ❌ BAD: {{"{{"sprint_id": "sprint_id"}}}} (placeholder!)
   - ✅ GOOD: {{"{{"sprint_id": "e6890ea6-0c3c-4a83-aa05-41b223df3284"}}}}

5. **Error Handling:**
   - If you get "tool not found" errors, check tool name (no parentheses!)
   - If you get 404 errors, verify you're using correct UUIDs (not placeholders)
   - If no sprints found, verify project_id is correct
   - If format errors occur, ensure Action and Action Input are on separate lines
   - ONLY say "This requires detailed planning" if task is truly complex
   - Simple sprint analysis → Answer directly!

6. **Research & Reasoning (CRITICAL):**
   - **ALWAYS include your reasoning in the message content** before calling tools
   - **Use web_search when you need to:**
     - Understand best practices for the task (e.g., "how to analyze sprint performance")
     - Research methodologies or frameworks
     - Get industry benchmarks or standards
     - Understand how to interpret or analyze data
     - Clarify ambiguous requests
   - **Research workflow:**
     1. Read the user's request
     2. Think: "Do I need external context or best practices?"
     3. If yes: Use web_search first to research
     4. Then: Use PM tools to get the data
     5. Finally: Combine research insights with data to provide comprehensive answer
   - **Example:** For "analyze sprint 4":
     - First: web_search("sprint analysis best practices agile")
     - Then: list_sprints → sprint_report
     - Finally: Provide analysis combining research insights with sprint data

{project_id_context}

Available tools:
{tools}

Tool names: {tool_names}

Question: {input}

{agent_scratchpad}"""
    
    # LangGraph uses state_modifier function instead of PromptTemplate
    # The state_modifier will be defined when creating the agent graph below
    
    # DEBUG: Log tool names for verification
    tool_names_list = [tool.name for tool in tools]
    logger.info(f"[REACT-AGENT] 🔍 DEBUG: Available tool names: {tool_names_list}")
    logger.info(f"[REACT-AGENT] 🔍 DEBUG: Project ID in context: {project_id if project_id else 'None'}")
    logger.info(f"[REACT-AGENT] 🔍 DEBUG: User query: {user_query}")
    
    # CRITICAL FIX: Monitor scratchpad token usage with callback
    # Callbacks can't modify prompts, but we can detect when scratchpad is too large
    # and escalate to planner before hitting rate limits
    from langchain_core.callbacks import BaseCallbackHandler
    
    class ScratchpadTokenMonitor(BaseCallbackHandler):
        """Monitor scratchpad token usage and escalate if too large."""
        
        def __init__(self, model_name, max_scratchpad_tokens=10000):
            super().__init__()
            self.model_name = model_name
            self.max_scratchpad_tokens = max_scratchpad_tokens
            self.prompt_tokens = []
            self.should_escalate = False
            self.captured_messages = []  # Store messages for detailed logging
            self.iteration_count = 0
        
        def on_llm_start(self, serialized, prompts, **kwargs):
            """Monitor prompt tokens before LLM call."""
            if not prompts:
                return
            
            try:
                import tiktoken
                try:
                    encoding = tiktoken.encoding_for_model(self.model_name)
                except:
                    encoding = tiktoken.get_encoding("cl100k_base")
                
                prompt_text = prompts[0] if isinstance(prompts[0], str) else str(prompts[0])
                prompt_tokens = len(encoding.encode(prompt_text))
                self.prompt_tokens.append(prompt_tokens)
                
                if prompt_tokens > self.max_scratchpad_tokens:
                    logger.error(
                        f"[REACT-AGENT] 🚨 CRITICAL: Scratchpad too large: {prompt_tokens:,} tokens "
                        f"(limit: {self.max_scratchpad_tokens:,}). Tool truncation is NOT working!"
                    )
                    self.should_escalate = True
                else:
                    logger.debug(
                        f"[REACT-AGENT] 🔍 Scratchpad token count: {prompt_tokens:,} tokens "
                        f"(limit: {self.max_scratchpad_tokens:,})"
                    )
            except Exception as e:
                logger.error(f"[REACT-AGENT] ❌ Error monitoring scratchpad: {e}")
    
    # Create callback to monitor scratchpad
    scratchpad_monitor = ScratchpadTokenMonitor(
        model_name=actual_model_name,
        max_scratchpad_tokens=10000  # Max 10K tokens for scratchpad (should be safe with tool truncation)
    )
    
    # Create LangGraph ReAct agent (returns a graph, not an executor)
    # LangGraph provides better scratchpad control and context management
    # Based on src/agents/agents.py, LangGraph's create_react_agent uses 'prompt' parameter
    # The prompt function receives state and should return messages (typically via apply_prompt_template)
    # But we have a custom prompt template, so we'll format it directly
    
    # Format the prompt template
    formatted_template = react_prompt_template.replace("{project_id_context}", project_id_context)
    
    # Create prompt function for LangGraph
    # CRITICAL: LangGraph's create_react_agent uses STRUCTURED TOOL CALLING, not text-based ReAct format!
    # The LLM should use tool calls directly, not "Action: tool_name" text format.
    # We need a simpler system prompt that doesn't confuse the LLM.
    def react_prompt_func(state: dict):
        """Prompt function for LangGraph - returns simple system prompt for tool calling."""
        # LangGraph handles tool calling automatically, so we just need a simple system prompt
        # Include project_id context if available
        system_prompt = f"""You are a helpful PM assistant with access to project management tools.

{project_id_context}

Use the available tools to answer the user's question. When you need to use a tool, call it directly using the tool calling feature.

**CRITICAL RULES (in priority order):**
1. **If project_id is provided above (in the PROJECT ID section):**
   - **DO NOT call `list_projects`** - the project is already identified!
   - Use the provided project_id directly in tool calls (e.g., `list_users(project_id="...")`)
   - For "show me all users in this project" → Call `list_users` with the provided project_id
   - For "list sprints" → Call `list_sprints` with the provided project_id
   - Only use `get_project` if you need project details/metadata

2. **If NO project_id is provided:**
   - If user mentions a project NAME, first call `list_projects` to find the project_id
   - Then use that project_id in subsequent tool calls

3. **General tool usage:**
   - Tool names do NOT have parentheses: use `list_sprints` NOT `list_sprints()`
   - Always use actual UUIDs from tool results, not placeholder strings
   - For sprint analysis: list_sprints → get_sprint → sprint_report (if project_id is already provided, skip list_projects)

Available tools:
{chr(10).join([f"- {tool.name}: {tool.description}" for tool in tools])}

Answer the user's question using the tools as needed."""
        
        # Return as SystemMessage (LangGraph expects list of messages to prepend)
        from langchain_core.messages import SystemMessage
        return [SystemMessage(content=system_prompt)]
    
    # CRITICAL: Use LangGraph's native pre_model_hook with Cursor-style context tracking
    # This tracks cumulative usage across all tools/agents and auto-optimizes at 100%
    def react_pre_model_hook(state: dict):
        """
        LangGraph pre_model_hook: Cursor-style context optimization.
        
        - Tracks cumulative usage across all tools/agents
        - Auto-optimizes when reaching 100%
        - Allocates context as percentages (like Cursor)
        """
        from src.utils.cursor_style_context_tracker import get_global_tracker
        
        # Get messages from state
        messages = state.get("messages", [])
        if not messages:
            return state
        
        # Get or create Cursor-style tracker
        tracker = get_global_tracker()
        if not tracker:
            # Create tracker if it doesn't exist (first call in request)
            from src.utils.cursor_style_context_tracker import create_tracker_for_request
            tracker = create_tracker_for_request(model_context_limit)
            
            # Allocate percentages to agents/tools (Cursor-style)
            from src.utils.adaptive_context_config import get_agent_strategy
            strategy = get_agent_strategy("react_agent")
            tracker.allocate(
                "react_agent",
                strategy.get("token_percent", 0.35),
                "ReAct agent context"
            )
            # Allocate for tools (each tool gets a small percentage)
            for tool in tools:
                tracker.allocate(
                    f"tool_{tool.name}",
                    0.05,  # 5% per tool (adjust as needed)
                    f"Tool: {tool.name}"
                )
        
        # Count tokens in current messages
        try:
            token_count = context_manager.count_tokens(messages, model=actual_model_name)
            
            # Record usage in tracker
            needs_optimize, reason = tracker.record_usage("react_agent", token_count, messages)
            
            # Check if we should optimize
            should_optimize, optimize_reason = tracker.should_optimize()
            
            if should_optimize:
                logger.info(
                    f"[REACT-AGENT] 🔄 Cursor-style auto-optimization triggered: {optimize_reason}"
                )
                # Perform optimization
                opt_metadata = tracker.optimize(context_manager)
                logger.info(
                    f"[REACT-AGENT] ✅ Optimization complete - "
                    f"Freed {opt_metadata.get('freed_tokens', 0):,} tokens, "
                    f"Usage: {opt_metadata.get('usage_percentage', 0):.0%}"
                )
                
                # Compress messages after optimization
                compressed_state = context_manager.compress_messages({"messages": messages})
                if isinstance(compressed_state, dict):
                    compressed_messages = compressed_state.get("messages", [])
                    if compressed_messages:
                        logger.debug(
                            f"[REACT-AGENT] 🔍 pre_model_hook: Compressed {len(messages)} → {len(compressed_messages)} messages "
                            f"({token_count:,} → {context_manager.count_tokens(compressed_messages, model=actual_model_name):,} tokens)"
                        )
                        state["messages"] = compressed_messages
            else:
                # Normal compression (if over limit)
                if context_manager.is_over_limit(messages):
                    compressed_state = context_manager.compress_messages({"messages": messages})
                    if isinstance(compressed_state, dict):
                        compressed_messages = compressed_state.get("messages", [])
                        if compressed_messages:
                            logger.debug(
                                f"[REACT-AGENT] 🔍 pre_model_hook: Compressed {len(messages)} → {len(compressed_messages)} messages"
                            )
                            state["messages"] = compressed_messages
                
                # Log usage status
                usage_pct = tracker.get_total_usage_percentage()
                if usage_pct > 0.5:  # Log if usage > 50%
                    logger.debug(
                        f"[REACT-AGENT] 📊 Context usage: {usage_pct:.0%} "
                        f"({tracker.total_used:,}/{tracker.total_limit:,} tokens)"
                    )
                    
        except Exception as e:
            logger.warning(f"[REACT-AGENT] ⚠️ pre_model_hook failed: {e}")
            # Continue with original messages if tracking fails
        
        return state
    
    agent_graph = create_react_agent(
        model=llm,
        tools=tools,
        prompt=react_prompt_func,  # LangGraph uses 'prompt' parameter (function that returns messages)
        pre_model_hook=react_pre_model_hook,  # ✅ Use LangGraph's native context optimization!
        interrupt_before=[],  # No interrupts needed for fast path
        checkpointer=None,  # No checkpointing for fast path
    )
    
    logger.info("[REACT-AGENT] ✅ Created LangGraph ReAct agent (better scratchpad control)")
    
    # Execute ReAct loop with proper iteration limits (NOT timeout - that's a bad workaround)
    # LangGraph's recursion_limit properly stops the agent after N iterations
    # This is better than timeout because it doesn't interrupt legitimate processing
    try:
        logger.info(f"[REACT-AGENT] 🔍 DEBUG: Starting executor.ainvoke() with query: {user_query[:100]}...")
        logger.info(f"[REACT-AGENT] 🔍 DEBUG: Using compressed messages: {len(compressed_messages)} messages ({compressed_token_count:,} tokens)")
        
        try:
            # DEBUG: Log what we're about to send
            logger.info(
                f"[REACT-AGENT] 🔍 DEBUG: About to call executor.ainvoke() with:\n"
                f"  - input: {user_query[:200]}...\n"
                f"  - state messages count: {len(all_messages)}\n"
                f"  - compressed messages count: {len(compressed_messages)}\n"
                f"  - compressed tokens: {compressed_token_count:,}\n"
                f"  - NOTE: LangGraph agent manages scratchpad internally with better control"
            )
            
            # LangGraph agent expects state dict with "messages" key
            # Use compressed messages (pre_model_hook will further optimize if needed)
            from langchain_core.messages import HumanMessage
            # Include compressed context + current query
            # pre_model_hook will optimize this further before each model call
            agent_state = {
                "messages": compressed_messages + [HumanMessage(content=user_query)]
            }
            
            # Invoke LangGraph agent (returns state dict, not executor result)
            # Use recursion_limit to prevent infinite loops (NOT timeout - that's a bad workaround)
            # recursion_limit controls max iterations, which is the proper way to limit ReAct loops
            recursion_limit = 8  # Same as our escalation threshold - allows complex queries but prevents loops
            logger.info(f"[REACT-AGENT] 🔍 Starting LangGraph agent.ainvoke() with recursion_limit={recursion_limit}")
            
            # Use astream to capture state incrementally so we can log what happened even if recursion limit is hit
            result_state = {"messages": []}
            incremental_thoughts = []  # Track thoughts as they're generated
            try:
                async for chunk in agent_graph.astream(
                    agent_state, 
                    config={
                        "callbacks": [scratchpad_monitor],
                        "recursion_limit": recursion_limit  # Proper iteration limit, not timeout
                    }
                ):
                    # Accumulate state from each chunk
                    for node_name, state_update in chunk.items():
                        if isinstance(state_update, dict):
                            if "messages" in state_update:
                                new_messages = state_update["messages"]
                                result_state["messages"].extend(new_messages)
                                
                                # Extract thoughts incrementally from new messages
                                for msg in new_messages:
                                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                                        # Extract thought from this message
                                        thought_text = None
                                        
                                        # Method 1: Check additional_kwargs for reasoning_content
                                        if hasattr(msg, 'additional_kwargs') and msg.additional_kwargs:
                                            reasoning_content = msg.additional_kwargs.get('reasoning_content', '')
                                            if reasoning_content and isinstance(reasoning_content, str):
                                                thought_text = reasoning_content.strip()
                                        
                                        # Method 2: Extract from content
                                        if not thought_text:
                                            msg_content = getattr(msg, 'content', '') or ''
                                            if msg_content and isinstance(msg_content, str):
                                                if "Thought:" in msg_content:
                                                    thought_match = msg_content.split("Thought:")[-1].split("Action:")[0].strip()
                                                    if thought_match:
                                                        thought_text = thought_match
                                                elif msg_content and not msg_content.startswith("Question:"):
                                                    thought_text = msg_content[:200].strip()
                                                    if len(msg_content) > 200:
                                                        thought_text += "..."
                                        
                                        # Method 3: Generate based on tool
                                        if not thought_text and msg.tool_calls:
                                            tool_names = [tc.get('name') if isinstance(tc, dict) else getattr(tc, 'name', 'unknown') for tc in msg.tool_calls]
                                            if tool_names:
                                                thought_text = f"I need to use {', '.join(tool_names)} to answer the user's question."
                                        
                                        if thought_text:
                                            incremental_thoughts.append({
                                                "thought": thought_text,
                                                "before_tool": True,
                                                "step_index": len(incremental_thoughts)
                                            })
                                            logger.info(f"[REACT-AGENT] 💭 Extracted incremental thought: {thought_text[:100]}...")
                                            
                                            # Add thought to message's additional_kwargs so it gets streamed
                                            if not hasattr(msg, 'additional_kwargs') or not msg.additional_kwargs:
                                                msg.additional_kwargs = {}
                                            msg.additional_kwargs["react_thoughts"] = incremental_thoughts.copy()
                            
                            # Merge other state fields
                            for key, value in state_update.items():
                                if key != "messages":
                                    result_state[key] = value
            except Exception as stream_error:
                # Re-raise to be caught by outer handler, but result_state now has partial data
                raise
            
            # Extract result from LangGraph state
            # LangGraph returns state with "messages" containing the final response
            result_messages = result_state.get("messages", [])
            logger.info(f"[REACT-AGENT] 🔍 DEBUG: LangGraph returned state with {len(result_messages)} messages")
            logger.info(f"[REACT-AGENT] 🔍 DEBUG: State keys: {list(result_state.keys())}")
            
            if result_messages:
                # Get the last AI message as the output
                last_message = result_messages[-1]
                if hasattr(last_message, 'content'):
                    output = last_message.content
                else:
                    output = str(last_message)
            else:
                output = ""
            
            # Extract intermediate steps from LangGraph state
            # LangGraph stores tool calls and results in messages
            # Cursor-style: Extract "Thought" (reasoning) before tool calls
            intermediate_steps = []
            thoughts = []  # Store thoughts separately for Cursor-style display
            logger.info(f"[REACT-AGENT] 🔍 DEBUG: Extracting intermediate steps from {len(result_messages)} messages")
            
            # Debug: Log message types and extract Thought/Action/Observation (use INFO level so it shows up)
            iteration_count = 0
            for i, msg in enumerate(result_messages):
                msg_type = type(msg).__name__
                has_tool_calls = hasattr(msg, 'tool_calls') and bool(msg.tool_calls)
                has_tool_call_id = hasattr(msg, 'tool_call_id') and bool(msg.tool_call_id)
                tool_calls_count = len(msg.tool_calls) if hasattr(msg, 'tool_calls') and msg.tool_calls else 0
                content = str(getattr(msg, 'content', '')) if hasattr(msg, 'content') else ''
                content_preview = content[:200] if content else 'N/A'
                
                # Extract Thought/Action/Observation from AIMessage content
                if msg_type == "AIMessage" and content:
                    # Look for Thought/Action pattern in content
                    import re
                    thought_match = re.search(r"Thought:\s*(.*?)(?=Action:|$)", content, re.DOTALL)
                    action_match = re.search(r"Action:\s*(.*?)(?=Action Input:|Observation:|$)", content, re.DOTALL)
                    action_input_match = re.search(r"Action Input:\s*(.*?)(?=Observation:|$)", content, re.DOTALL)
                    
                    if thought_match or action_match:
                        iteration_count += 1
                        thought = thought_match.group(1).strip() if thought_match else "N/A"
                        action = action_match.group(1).strip() if action_match else "N/A"
                        action_input = action_input_match.group(1).strip() if action_input_match else "N/A"
                        
                        logger.info(
                            f"[REACT-AGENT] 🔍 ITERATION {iteration_count} - AIMessage {i}:\n"
                            f"  Thought: {thought[:300]}...\n"
                            f"  Action: {action}\n"
                            f"  Action Input: {action_input[:200]}..."
                        )
                
                # Log ToolMessage with observation
                if msg_type == "ToolMessage" and has_tool_call_id:
                    tool_name = getattr(msg, 'name', 'unknown')
                    tool_call_id = getattr(msg, 'tool_call_id', 'N/A')
                    obs_content = content[:500] if content else 'N/A'
                    logger.info(
                        f"[REACT-AGENT] 🔍 OBSERVATION - ToolMessage {i}:\n"
                        f"  Tool: {tool_name}\n"
                        f"  Tool Call ID: {tool_call_id}\n"
                        f"  Observation: {obs_content}..."
                    )
                
                # Check for reasoning_content in additional_kwargs (LangGraph might store it there)
                reasoning = getattr(msg, 'additional_kwargs', {}).get('reasoning_content', '') if hasattr(msg, 'additional_kwargs') else ''
                logger.info(
                    f"[REACT-AGENT] 🔍 Message {i}: type={msg_type}, "
                    f"has_tool_calls={has_tool_calls} ({tool_calls_count} calls), "
                    f"has_tool_call_id={has_tool_call_id}, "
                    f"content_len={len(content)}, "
                    f"content_preview={content_preview[:100]}..., "
                    f"reasoning_content={bool(reasoning)}"
                )
            
            for i, msg in enumerate(result_messages):
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    # This is a tool-calling message
                    logger.info(f"[REACT-AGENT] 🔍 Found tool-calling message at index {i} with {len(msg.tool_calls)} tool calls")
                    
                    # Cursor-style: Extract "Thought" from AIMessage content before tool calls
                    # LangGraph's structured tool calling may store reasoning in different places
                    thought_text = None
                    
                    # Method 1: Check additional_kwargs for reasoning_content (LangGraph/OpenAI format)
                    if hasattr(msg, 'additional_kwargs') and msg.additional_kwargs:
                        reasoning_content = msg.additional_kwargs.get('reasoning_content', '')
                        if reasoning_content and isinstance(reasoning_content, str):
                            thought_text = reasoning_content.strip()
                            logger.info(f"[REACT-AGENT] 💭 Found reasoning_content in additional_kwargs: {len(thought_text)} chars")
                    
                    # Method 2: Check AIMessage content (text-based ReAct format)
                    if not thought_text:
                        msg_content = getattr(msg, 'content', '') or ''
                        if msg_content and isinstance(msg_content, str):
                            # Try to extract thought/reasoning from content
                            # Common patterns: "Thought:", "I need to", "Let me", etc.
                            if "Thought:" in msg_content:
                                # Extract text after "Thought:"
                                thought_match = msg_content.split("Thought:")[-1].split("Action:")[0].strip()
                                if thought_match:
                                    thought_text = thought_match
                            elif msg_content and not msg_content.startswith("Question:"):
                                # If content exists and isn't just a question, treat it as reasoning
                                # Limit to first 200 chars to avoid including tool call details
                                thought_text = msg_content[:200].strip()
                                if len(msg_content) > 200:
                                    thought_text += "..."
                    
                    # Method 3: Generate a descriptive thought based on tool being called (fallback)
                    if not thought_text and msg.tool_calls:
                        # Create a descriptive thought based on the tool being called
                        tool_names = [tc.get('name') if isinstance(tc, dict) else getattr(tc, 'name', 'unknown') for tc in msg.tool_calls]
                        tool_args = []
                        for tc in msg.tool_calls:
                            args = tc.get('args', {}) if isinstance(tc, dict) else getattr(tc, 'args', {})
                            if args:
                                tool_args.append(args)
                        
                        if tool_names:
                            # Create a more descriptive thought
                            if len(tool_names) == 1:
                                tool_name = tool_names[0]
                                if tool_args and tool_args[0]:
                                    # Include key args in the thought
                                    args_str = ", ".join([f"{k}={v}" for k, v in list(tool_args[0].items())[:2]])
                                    thought_text = f"I'll use {tool_name}({args_str}) to get the information I need."
                                else:
                                    thought_text = f"I'll use {tool_name} to get the information I need."
                            else:
                                thought_text = f"I'll use {', '.join(tool_names)} to gather the required information."
                            logger.info(f"[REACT-AGENT] 💭 Generated descriptive thought based on tool calls: {tool_names}")
                    
                    if thought_text:
                        thoughts.append({
                            "thought": thought_text,
                            "before_tool": True,
                            "step_index": len(intermediate_steps)
                        })
                        logger.info(f"[REACT-AGENT] 💭 Extracted thought: {thought_text[:100]}...")
                    else:
                        logger.warning(f"[REACT-AGENT] 💭 No thought found in message {i} (content empty, no reasoning_content, no tool_calls)")
                    
                    for tool_call in msg.tool_calls:
                        tool_call_id = tool_call.get('id') if isinstance(tool_call, dict) else getattr(tool_call, 'id', None)
                        tool_name = tool_call.get('name') if isinstance(tool_call, dict) else getattr(tool_call, 'name', 'unknown')
                        logger.debug(f"[REACT-AGENT] 🔍 Looking for tool result for call_id={tool_call_id}, tool={tool_name}")
                        
                        # Find corresponding tool result in subsequent messages
                        tool_result = None
                        for j in range(i + 1, len(result_messages)):
                            result_msg = result_messages[j]
                            result_tool_call_id = getattr(result_msg, 'tool_call_id', None)
                            if result_tool_call_id == tool_call_id:
                                tool_result = result_msg.content if hasattr(result_msg, 'content') else str(result_msg)
                                logger.debug(f"[REACT-AGENT] 🔍 Found tool result for {tool_name} at index {j}")
                                break
                        
                        if tool_result:
                            # Create a tuple compatible with AgentExecutor format
                            # AgentExecutor uses (AgentAction, observation) tuples
                            from langchain_core.agents import AgentAction
                            action = AgentAction(
                                tool=tool_name,
                                tool_input=tool_call.get('args', {}) if isinstance(tool_call, dict) else getattr(tool_call, 'args', {}),
                                log=f"Tool: {tool_name}"
                            )
                            intermediate_steps.append((action, tool_result))
                        else:
                            logger.warning(f"[REACT-AGENT] ⚠️ No tool result found for {tool_name} (call_id={tool_call_id})")
            
            # Store thoughts in result for frontend display
            if thoughts:
                logger.info(f"[REACT-AGENT] 💭 Extracted {len(thoughts)} thought(s) for Cursor-style display")
            
            logger.info(f"[REACT-AGENT] 🔍 Extracted {len(intermediate_steps)} intermediate steps")
            
            # Create result dict compatible with existing code
            result = {
                "output": output,
                "intermediate_steps": intermediate_steps,
                "thoughts": thoughts  # Cursor-style: Include thoughts for UI display
            }
            
            # Check if scratchpad monitor detected issues
            if scratchpad_monitor.should_escalate:
                output = result.get("output", "")
                logger.error(
                    f"[REACT-AGENT] 🚨 Escalating to planner: Scratchpad exceeded token limit. "
                    f"Max prompt tokens: {max(scratchpad_monitor.prompt_tokens) if scratchpad_monitor.prompt_tokens else 0:,}"
                )
                return Command(
                    update={
                        "escalation_reason": f"scratchpad_too_large: max_tokens={max(scratchpad_monitor.prompt_tokens) if scratchpad_monitor.prompt_tokens else 0}",
                        "react_attempts": intermediate_steps,
                        "react_thoughts": thoughts,  # Preserve thoughts when escalating
                        "partial_result": output or "ReAct agent scratchpad exceeded token limit. Escalating to full pipeline.",
                        "goto": "planner"
                    },
                    goto="planner"
                )
            
            logger.info(f"[REACT-AGENT] 🔍 DEBUG: LangGraph agent.ainvoke() completed successfully")
            if scratchpad_monitor.prompt_tokens:
                logger.info(
                    f"[REACT-AGENT] 🔍 Scratchpad token usage: "
                    f"min={min(scratchpad_monitor.prompt_tokens):,}, "
                    f"max={max(scratchpad_monitor.prompt_tokens):,}, "
                    f"avg={sum(scratchpad_monitor.prompt_tokens)//len(scratchpad_monitor.prompt_tokens):,}"
                )
        except asyncio.TimeoutError:
            logger.error(
                f"[REACT-AGENT] ⏱️ TIMEOUT: LangGraph agent.ainvoke() exceeded 60 second timeout. "
                f"Escalating to planner. This may indicate the agent is looping or taking too long."
            )
            
            # Extract any intermediate steps that were completed before timeout
            # This allows tool calls to still show in the UI even if ReAct times out
            partial_intermediate_steps = []
            partial_thoughts = []
            try:
                # Try to extract partial results from result_state if available
                if 'result_state' in locals() and result_state:
                    result_messages = result_state.get("messages", [])
                    # Extract any tool calls that were made before timeout
                    for i, msg in enumerate(result_messages):
                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                            # Extract thoughts if available
                            if i > 0:
                                prev_msg = result_messages[i-1]
                                if isinstance(prev_msg, AIMessage) and hasattr(prev_msg, 'content'):
                                    thought_match = re.search(r"Thought:\s*(.*)", prev_msg.content, re.DOTALL)
                                    if thought_match:
                                        partial_thoughts.append({
                                            "thought": thought_match.group(1).strip(),
                                            "step_index": len(partial_intermediate_steps) + 1
                                        })
                            
                            # Extract tool calls
                            for tool_call in msg.tool_calls:
                                tool_call_id = tool_call.get('id') if isinstance(tool_call, dict) else getattr(tool_call, 'id', None)
                                tool_name = tool_call.get('name') if isinstance(tool_call, dict) else getattr(tool_call, 'name', 'unknown')
                                
                                # Find corresponding tool result
                                tool_result = None
                                for j in range(i + 1, len(result_messages)):
                                    result_msg = result_messages[j]
                                    result_tool_call_id = getattr(result_msg, 'tool_call_id', None)
                                    if result_tool_call_id == tool_call_id:
                                        tool_result = result_msg.content if hasattr(result_msg, 'content') else str(result_msg)
                                        break
                                
                                if tool_result:
                                    from langchain_core.agents import AgentAction
                                    action = AgentAction(
                                        tool=tool_name,
                                        tool_input=tool_call.get('args', {}) if isinstance(tool_call, dict) else getattr(tool_call, 'args', {}),
                                        log=f"Tool: {tool_name}"
                                    )
                                    partial_intermediate_steps.append((action, tool_result))
            except Exception as extract_error:
                logger.warning(f"[REACT-AGENT] Failed to extract partial steps on timeout: {extract_error}")
            
            # Convert partial intermediate steps to messages for frontend display
            tool_call_messages = []
            if partial_intermediate_steps:
                logger.info(f"[REACT-AGENT] 🔧 Converting {len(partial_intermediate_steps)} partial intermediate steps to tool call messages")
                import uuid
                from langchain_core.messages import AIMessage, ToolMessage
                
                for step_idx, step in enumerate(partial_intermediate_steps):
                    if isinstance(step, (list, tuple)) and len(step) >= 2:
                        action = step[0]
                        observation = step[1]
                        tool_name = getattr(action, 'tool', None) or (action.tool if hasattr(action, 'tool') else 'unknown')
                        tool_input = getattr(action, 'tool_input', None) or (action.tool_input if hasattr(action, 'tool_input') else {})
                        tool_call_id = f"react_call_{uuid.uuid4().hex[:8]}_{step_idx}"
                        
                        tool_call_msg = AIMessage(
                            content="",
                            name="react_agent",
                            tool_calls=[{
                                "id": tool_call_id,
                                "name": tool_name,
                                "args": tool_input if isinstance(tool_input, dict) else {}
                            }]
                        )
                        tool_call_messages.append(tool_call_msg)
                        
                        tool_result_msg = ToolMessage(
                            content=str(observation)[:10000],
                            tool_call_id=tool_call_id,
                            name=tool_name
                        )
                        tool_call_messages.append(tool_result_msg)
            
            return_messages = tool_call_messages if tool_call_messages else []
            
            return Command(
                update={
                    "messages": return_messages,
                    "escalation_reason": "executor_timeout",
                    "react_intermediate_steps": partial_intermediate_steps,
                    "react_thoughts": partial_thoughts,  # Preserve thoughts even on timeout
                    "partial_result": "ReAct agent execution timed out. Escalating to full pipeline.",
                    "goto": "planner"
                },
                goto="planner"
            )
        
        output = result.get("output", "")
        intermediate_steps = result.get("intermediate_steps", [])
        
        logger.info(f"[REACT-AGENT] Completed in {len(intermediate_steps)} iterations")
        
        # DEBUG: Log intermediate steps structure and token counts with DETAILED analysis
        if intermediate_steps:
            logger.info(f"[REACT-AGENT] 🔍 DEBUG: Intermediate steps structure: {len(intermediate_steps)} steps")
            total_obs_tokens = 0
            error_count = 0
            invalid_tool_count = 0
            placeholder_count = 0
            
            for idx, step in enumerate(intermediate_steps):
                logger.info(f"[REACT-AGENT] 🔍 DEBUG: Step {idx + 1}: type={type(step)}, len={len(step) if isinstance(step, (list, tuple)) else 'N/A'}")
                if isinstance(step, (list, tuple)) and len(step) >= 2:
                    action = step[0]
                    observation = step[1]
                    
                    # Extract tool name and input from action
                    tool_name = None
                    tool_input = None
                    if hasattr(action, 'tool'):
                        tool_name = action.tool
                    elif hasattr(action, 'tool_input'):
                        tool_input = action.tool_input
                    
                    # Check for common errors
                    obs_str = str(observation)
                    obs_lower = obs_str.lower()
                    
                    # Check for invalid tool name (with parentheses)
                    if tool_name and "()" in tool_name:
                        invalid_tool_count += 1
                        logger.error(f"[REACT-AGENT] ❌ ERROR: Step {idx + 1} - Invalid tool name with parentheses: {tool_name}")
                    
                    # Check for placeholder values
                    if tool_input:
                        tool_input_str = str(tool_input)
                        if '"project_id": "project_id"' in tool_input_str or '"sprint_id": "sprint_id"' in tool_input_str:
                            placeholder_count += 1
                            logger.error(f"[REACT-AGENT] ❌ ERROR: Step {idx + 1} - Placeholder values detected: {tool_input_str[:200]}")
                    
                    # Check for errors in observation
                    if any(err in obs_lower for err in ["error", "failed", "exception", "invalid", "not found", "not a valid tool"]):
                        error_count += 1
                        logger.warning(f"[REACT-AGENT] ⚠️ ERROR DETECTED in Step {idx + 1}: {obs_str[:300]}")
                    
                    action_str = str(action)[:200] if action else "None"
                    obs_len = len(obs_str)
                    
                    # CRITICAL: Count tokens in observation and check if too large
                    obs_tokens = 0
                    try:
                        import tiktoken
                        try:
                            encoding = tiktoken.encoding_for_model(actual_model_name)
                        except:
                            encoding = tiktoken.get_encoding("cl100k_base")
                        obs_tokens = len(encoding.encode(obs_str))
                        total_obs_tokens += obs_tokens
                        
                        # CRITICAL: Log observation size to verify truncation is working
                        logger.info(
                            f"[REACT-AGENT] 🔍 Step {idx + 1} observation: "
                            f"{obs_len:,} chars, {obs_tokens:,} tokens "
                            f"(tool: {tool_name or 'unknown'})"
                        )
                        
                        # CRITICAL: Check if observation is too large (should be truncated to 1000 tokens)
                        # If we see > 3000 tokens, the truncation wrapper might not be working
                        if obs_tokens > 3000:
                            logger.error(
                                f"[REACT-AGENT] 🚨 CRITICAL: Step {idx + 1} observation has {obs_tokens:,} tokens "
                                f"(expected max 2000). Tool truncation may not be working! Escalating immediately."
                            )
                            return Command(
                                update={
                                    "escalation_reason": f"tool_result_too_large: step_{idx+1}_has_{obs_tokens}_tokens",
                                    "react_attempts": intermediate_steps[:idx+1],
                                    "partial_result": output,
                                    "goto": "planner"
                                },
                                goto="planner"
                            )
                        logger.info(
                            f"[REACT-AGENT] 🔍 DEBUG: Step {idx + 1} - "
                            f"Tool: {tool_name if tool_name else 'N/A'}, "
                            f"Input: {str(tool_input)[:100] if tool_input else 'N/A'}, "
                            f"Observation: {obs_len:,} chars, {obs_tokens:,} tokens"
                        )
                    except Exception as e:
                        logger.warning(f"[REACT-AGENT] Failed to count tokens in observation: {e}")
                        # Estimate tokens as fallback
                        obs_tokens = obs_len // 4
                        total_obs_tokens += obs_tokens
                        logger.info(f"[REACT-AGENT]   Action: {action_str}")
                        logger.info(f"[REACT-AGENT]   Observation: {obs_str[:200]}...")
            
            logger.info(
                f"[REACT-AGENT] 🔍 DEBUG: Summary - "
                f"Total steps: {len(intermediate_steps)}, "
                f"Errors: {error_count}, "
                f"Invalid tool names: {invalid_tool_count}, "
                f"Placeholder values: {placeholder_count}, "
                f"Total observation tokens: {total_obs_tokens:,}"
            )
            
            # CRITICAL: Check if total observation tokens exceed safe limit
            # If observations alone are > 10K tokens, escalate to prevent rate limit
            safe_obs_limit = 10000  # 10K tokens for all observations combined
            if total_obs_tokens > safe_obs_limit:
                logger.error(
                    f"[REACT-AGENT] 🚨 CRITICAL: Total observation tokens ({total_obs_tokens:,}) "
                    f"exceed safe limit ({safe_obs_limit:,}). Escalating to prevent rate limit error."
                )
                return Command(
                    update={
                        "escalation_reason": f"observation_tokens_too_large: {total_obs_tokens}_tokens",
                        "react_attempts": intermediate_steps,
                        "partial_result": output,
                        "goto": "planner"
                    },
                    goto="planner"
                )
            
            # Early escalation if we detect too many errors
            if invalid_tool_count >= 2 or placeholder_count >= 2:
                logger.error(
                    f"[REACT-AGENT] ❌ CRITICAL: Detected {invalid_tool_count} invalid tool names and {placeholder_count} placeholder values. "
                    f"Escalating to planner immediately."
                )
                return Command(
                    update={
                        "escalation_reason": f"tool_format_errors: invalid_tools={invalid_tool_count}, placeholders={placeholder_count}",
                        "partial_result": output,
                        "goto": "planner"
                    },
                    goto="planner"
                )
        else:
            logger.warning("[REACT-AGENT] ⚠️ No intermediate steps - agent may not have called any tools")
        
        # Check for escalation triggers
        
        # Trigger 1: Too many iterations (agent is struggling)
        # Reasonable limit: Escalate after 8 iterations to allow complex queries
        # Most queries need 2-4 tool calls, so 8 iterations gives plenty of room
        if len(intermediate_steps) >= 8:
            logger.warning(
                f"[REACT-AGENT] ⬆️ Too many iterations ({len(intermediate_steps)} >= 8) - escalating to planner. "
                f"This prevents infinite loops and token accumulation."
            )
            return Command(
                update={
                    "escalation_reason": f"max_iterations: {len(intermediate_steps)} iterations",
                    "react_attempts": intermediate_steps,
                    "react_thoughts": thoughts,  # Preserve thoughts when escalating
                    "partial_result": output,
                    "goto": "planner"  # Set goto in state for conditional edge
                },
                goto="planner"
            )
        
        # Trigger 2: Multiple errors detected (lower threshold to 2)
        error_count = 0
        error_details = []
        for idx, step in enumerate(intermediate_steps):
            observation = str(step[1]) if len(step) > 1 else ""
            obs_upper = observation.upper()
            if any(err in obs_upper for err in ["ERROR", "FAILED", "EXCEPTION", "INVALID", "NOT FOUND", "NOT A VALID TOOL"]):
                error_count += 1
                error_details.append(f"Step {idx + 1}: {observation[:200]}")
        
        if error_count >= 2:
            logger.warning(
                f"[REACT-AGENT] ⬆️ Multiple errors detected ({error_count} >= 2) - escalating to planner. "
                f"Error details: {error_details}"
            )
            return Command(
                update={
                    "escalation_reason": f"repeated_errors: {error_count} errors detected",
                    "react_attempts": intermediate_steps,
                    "react_thoughts": thoughts,  # Preserve thoughts when escalating
                    "partial_result": output,
                    "goto": "planner"  # Set goto in state for conditional edge
                },
                goto="planner"
            )
        
        # Trigger 3: Agent explicitly requests planning
        # ONLY escalate if agent explicitly says it needs planning
        # Don't escalate for informational responses
        escalation_phrases = [
            "this requires detailed planning",
            "i need to plan",
            "this is a complex task that requires",
            "this requires comprehensive analysis"
        ]
        if any(phrase in output.lower() for phrase in escalation_phrases):
            logger.info("[REACT-AGENT] ⬆️ Agent requested planning - escalating")
            return Command(
                update={
                    "escalation_reason": "agent_requested_planning",
                    "react_attempts": intermediate_steps,
                    "react_thoughts": thoughts,  # Preserve thoughts when escalating
                    "partial_result": output,
                    "goto": "planner"  # Set goto in state for conditional edge
                },
                goto="planner"
            )
        
        # Trigger 4: Data too large for reporter (CRITICAL FIX!)
        # Check if the collected data (including intermediate_steps/tool results) would exceed reporter's token limit
        # This prevents sending huge datasets to reporter only to fail
        
        # Count tokens accurately using tiktoken (not rough estimates!)
        try:
            import tiktoken
            
            # Get model name for accurate token counting
            try:
                model_name_for_encoding = getattr(llm, 'model_name', None) or getattr(llm, 'model', None) or "gpt-3.5-turbo"
            except:
                model_name_for_encoding = "gpt-3.5-turbo"
            
            # Get encoding for the model
            try:
                encoding = tiktoken.encoding_for_model(model_name_for_encoding)
            except (KeyError, ValueError):
                # Fallback to cl100k_base for GPT-3.5/4 models
                encoding = tiktoken.get_encoding("cl100k_base")
            
            # Count tokens in the ReAct output (accurate count)
            output_tokens = len(encoding.encode(output))
            
            # CRITICAL: Count tokens in intermediate_steps (tool results) - this is what reporter receives!
            intermediate_tokens = 0
            for step in intermediate_steps:
                if isinstance(step, (list, tuple)) and len(step) >= 2:
                    action = step[0]
                    observation = step[1]
                    # Count tokens in observation (tool result) - this can be HUGE!
                    obs_str = str(observation)
                    intermediate_tokens += len(encoding.encode(obs_str))
            
            # Count tokens in current state (accurate count for context)
            state_messages = state.get("messages", [])
            state_tokens = 0
            for msg in state_messages[-5:]:  # Last 5 messages for context
                if hasattr(msg, 'content'):
                    content_str = str(msg.content)
                    state_tokens += len(encoding.encode(content_str))
            
            # Total = output + tool results + state context
            total_estimated_tokens = output_tokens + intermediate_tokens + state_tokens
            
            # Get reporter's token limit (85% of model's context window)
            from src.llms.llm import get_llm_token_limit_by_type
            model_limit = get_llm_token_limit_by_type("basic") or 16385
            reporter_limit = int(model_limit * 0.85)  # Reporter uses 85%
            
            logger.info(
                f"[REACT-AGENT] 🔍 DEBUG: Token check for reporter - "
                f"output={output_tokens}, intermediate_steps={intermediate_tokens}, "
                f"state={state_tokens}, total={total_estimated_tokens}, "
                f"reporter_limit={reporter_limit}"
            )
            
            # If data is too large, escalate to full pipeline
            # Full pipeline will break it into smaller steps with validation
            if total_estimated_tokens > reporter_limit:
                logger.warning(
                    f"[REACT-AGENT] ⬆️ Data too large for reporter ({total_estimated_tokens:,} tokens > {reporter_limit:,} limit) - "
                    f"Intermediate steps alone: {intermediate_tokens:,} tokens. "
                    f"Escalating to full pipeline for incremental processing"
                )
                return Command(
                    update={
                        "escalation_reason": f"data_too_large_for_reporter ({total_estimated_tokens:,} tokens vs {reporter_limit:,} limit, intermediate_steps: {intermediate_tokens:,} tokens)",
                        "react_attempts": intermediate_steps,
                        "react_thoughts": thoughts,  # Preserve thoughts when escalating
                        "partial_result": output,
                        "goto": "planner"
                    },
                    goto="planner"
                )
        except Exception as token_check_error:
            # If token checking fails, log but don't block the flow
            logger.warning(f"[REACT-AGENT] ⚠️ Token check failed: {token_check_error}", exc_info=True)
        
        # CRITICAL: If no output and no intermediate steps, escalate to planner
        # This means the agent didn't execute properly (likely LangGraph issue)
        if not output and not intermediate_steps:
            logger.warning(
                "[REACT-AGENT] ⬆️ No output and no intermediate steps - agent didn't execute properly. "
                "Escalating to planner."
            )
            return Command(
                update={
                    "escalation_reason": "no_output_no_steps: LangGraph agent returned empty result",
                    "react_attempts": [],
                    "react_thoughts": [],
                    "partial_result": "",
                    "goto": "planner"
                },
                goto="planner"
            )
        
        # Success - return result to user
        logger.info(f"[REACT-AGENT] ✅ Success - returning answer ({len(output)} chars)")
        
        # Cursor-style: Include thoughts in state for UI display
        # Use incremental_thoughts if available (from streaming), otherwise extract from result
        thoughts = incremental_thoughts if 'incremental_thoughts' in locals() and incremental_thoughts else result.get("thoughts", [])
        
        # Convert intermediate_steps to AIMessage/ToolMessage pairs for frontend display
        # This allows tool calls to show up in the step box
        tool_call_messages = []
        if intermediate_steps:
            logger.info(f"[REACT-AGENT] 🔧 Converting {len(intermediate_steps)} intermediate steps to tool call messages for frontend")
            import uuid
            # AIMessage and ToolMessage are already imported at module level (line 14)
            
            for step_idx, step in enumerate(intermediate_steps):
                if isinstance(step, (list, tuple)) and len(step) >= 2:
                    action = step[0]  # AgentAction object
                    observation = step[1]  # Tool result
                    
                    # Extract tool name and input
                    tool_name = getattr(action, 'tool', None) or (action.tool if hasattr(action, 'tool') else 'unknown')
                    tool_input = getattr(action, 'tool_input', None) or (action.tool_input if hasattr(action, 'tool_input') else {})
                    
                    # Generate unique tool_call_id
                    tool_call_id = f"react_call_{uuid.uuid4().hex[:8]}_{step_idx}"
                    
                    # Create AIMessage with tool_calls (for frontend to display as tool call)
                    tool_call_msg = AIMessage(
                        content="",  # Empty content for tool-calling messages
                        name="react_agent",
                        tool_calls=[{
                            "id": tool_call_id,
                            "name": tool_name,
                            "args": tool_input if isinstance(tool_input, dict) else {}
                        }]
                    )
                    tool_call_messages.append(tool_call_msg)
                    
                    # Create ToolMessage with result (for frontend to display as result)
                    tool_result_msg = ToolMessage(
                        content=str(observation)[:10000],  # Limit result size
                        tool_call_id=tool_call_id,
                        name=tool_name
                    )
                    tool_call_messages.append(tool_result_msg)
                    
                    logger.debug(f"[REACT-AGENT] 🔧 Created tool call message pair: {tool_name} (id={tool_call_id})")
        
        # Include optimization messages if they exist
        return_messages = []
        if optimization_messages:
            return_messages.extend(optimization_messages)
        
        # Add tool call messages (AIMessage + ToolMessage pairs)
        return_messages.extend(tool_call_messages)
        
        # Add final output message with thoughts in additional_kwargs AND response_metadata for streaming
        # response_metadata is more reliably preserved through LangGraph state management
        final_message = AIMessage(content=output, name="react_agent")
        if thoughts:
            # Add to additional_kwargs (for compatibility)
            if not hasattr(final_message, 'additional_kwargs') or not final_message.additional_kwargs:
                final_message.additional_kwargs = {}
            final_message.additional_kwargs["react_thoughts"] = thoughts
            
            # Also add to response_metadata (more reliable)
            if not hasattr(final_message, 'response_metadata') or not final_message.response_metadata:
                final_message.response_metadata = {}
            final_message.response_metadata["react_thoughts"] = thoughts
            
            logger.info(f"[REACT-AGENT] 💭 Added {len(thoughts)} thoughts to final message (additional_kwargs + response_metadata) for streaming")
        return_messages.append(final_message)
        
        logger.info(f"[REACT-AGENT] 🔧 Returning {len(return_messages)} messages ({len(tool_call_messages)} tool call pairs + final output)")
        
        return Command(
            update={
                "messages": return_messages,
                "previous_result": output,  # Store for potential user feedback escalation
                "final_report": output,
                "react_intermediate_steps": intermediate_steps,
                "react_thoughts": thoughts,  # Cursor-style: Store thoughts for UI display (also in state for backend streaming)
                "routing_mode": "react_first",  # Mark that we used ReAct first
                "goto": "reporter"  # Set goto in state for conditional edge
            },
            goto="reporter"  # Route to reporter to finalize
        )
        
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        
        logger.error(
            f"[REACT-AGENT] ❌ Error during execution: {error_type}: {error_msg}",
            exc_info=True
        )
        
        # CRITICAL: If it's a GraphRecursionError, log what the agent was doing
        if error_type == "GraphRecursionError":
            try:
                # First, try to get messages from scratchpad monitor callback
                if hasattr(scratchpad_monitor, 'captured_messages') and scratchpad_monitor.captured_messages:
                    logger.warning(f"[REACT-AGENT] ⚠️ Hit recursion limit. Logging {len(scratchpad_monitor.captured_messages)} captured messages:")
                    for i, (msg_type, msg_data) in enumerate(scratchpad_monitor.captured_messages):
                        if msg_type == "AIMessage":
                            content = getattr(msg_data, 'content', '') if hasattr(msg_data, 'content') else str(msg_data)
                            tool_calls = getattr(msg_data, 'tool_calls', [])
                            if tool_calls:
                                tool_names = [tc.get('name', 'unknown') if isinstance(tc, dict) else getattr(tc, 'name', 'unknown') for tc in tool_calls]
                                tool_args = [str(tc.get('args', {})) if isinstance(tc, dict) else str(getattr(tc, 'args', {})) for tc in tool_calls]
                                logger.warning(
                                    f"[REACT-AGENT] 🔍 ITERATION {i+1} (BEFORE LIMIT) - AIMessage:\n"
                                    f"  Content: {str(content)[:500]}...\n"
                                    f"  Tool Calls: {tool_names}\n"
                                    f"  Tool Args: {tool_args}"
                                )
                        elif msg_type == "ToolMessage":
                            tool_name = msg_data.get('name', 'unknown')
                            tool_output = msg_data.get('output', 'N/A')
                            logger.warning(
                                f"[REACT-AGENT] 🔍 OBSERVATION (BEFORE LIMIT) - ToolMessage:\n"
                                f"  Tool: {tool_name}\n"
                                f"  Output: {str(tool_output)[:500]}..."
                            )
                
                # Extract messages from result_state (captured via astream)
                result_messages = result_state.get("messages", []) if result_state else []
                if result_messages:
                    logger.warning(f"[REACT-AGENT] ⚠️ Hit recursion limit. Logging {len(result_messages)} messages from result_state:")
                    
                    # Log all messages to see what happened
                    iteration_count = 0
                    for i, msg in enumerate(result_messages):
                        msg_type = type(msg).__name__
                        content = str(getattr(msg, 'content', '')) if hasattr(msg, 'content') else ''
                        
                        # Extract Thought/Action from AIMessage
                        if msg_type == "AIMessage" and content:
                            import re
                            thought_match = re.search(r"Thought:\s*(.*?)(?=Action:|$)", content, re.DOTALL)
                            action_match = re.search(r"Action:\s*(.*?)(?=Action Input:|Observation:|$)", content, re.DOTALL)
                            action_input_match = re.search(r"Action Input:\s*(.*?)(?=Observation:|$)", content, re.DOTALL)
                            
                            # Check for tool calls (LangGraph uses tool_calls, not Action: format)
                            tool_calls = getattr(msg, 'tool_calls', [])
                            
                            if thought_match or action_match or tool_calls:
                                iteration_count += 1
                                thought = thought_match.group(1).strip() if thought_match else "N/A"
                                action = action_match.group(1).strip() if action_match else "N/A"
                                action_input = action_input_match.group(1).strip() if action_input_match else "N/A"
                                
                                if tool_calls:
                                    tool_names = [tc.get('name', 'unknown') if isinstance(tc, dict) else getattr(tc, 'name', 'unknown') for tc in tool_calls]
                                    tool_args = [str(tc.get('args', {})) if isinstance(tc, dict) else str(getattr(tc, 'args', {})) for tc in tool_calls]
                                    logger.warning(
                                        f"[REACT-AGENT] 🔍 ITERATION {iteration_count} (FROM RESULT_STATE) - AIMessage {i}:\n"
                                        f"  Content: {content[:500]}...\n"
                                        f"  Tool Calls: {tool_names}\n"
                                        f"  Tool Args: {tool_args}"
                                    )
                                else:
                                    logger.warning(
                                        f"[REACT-AGENT] 🔍 ITERATION {iteration_count} (FROM RESULT_STATE) - AIMessage {i}:\n"
                                        f"  Thought: {thought[:300]}...\n"
                                        f"  Action: {action}\n"
                                        f"  Action Input: {action_input[:200]}..."
                                    )
                        
                        # Log ToolMessage observations
                        if msg_type == "ToolMessage":
                            tool_name = getattr(msg, 'name', 'unknown')
                            tool_call_id = getattr(msg, 'tool_call_id', 'N/A')
                            obs_content = content[:500] if content else 'N/A'
                            logger.warning(
                                f"[REACT-AGENT] 🔍 OBSERVATION (FROM RESULT_STATE) - ToolMessage {i}:\n"
                                f"  Tool: {tool_name}\n"
                                f"  Tool Call ID: {tool_call_id}\n"
                                f"  Observation: {obs_content}..."
                            )
            except Exception as log_error:
                logger.error(f"[REACT-AGENT] Error logging partial execution: {log_error}")
        
        # Check if it's a rate limit error
        if "rate_limit" in error_msg.lower() or "429" in error_msg or "too large" in error_msg.lower():
            logger.error(
                f"[REACT-AGENT] 🚨 RATE LIMIT ERROR DETECTED: {error_msg}. "
                f"This should have been caught by pre-flight check. "
                f"Original tokens: {original_token_count:,}, "
                f"Compressed tokens: {compressed_token_count:,}, "
                f"Estimated total: {total_estimated_tokens:,}, "
                f"Model limit: {model_context_limit:,}"
            )
        
        # Escalate on errors
        return Command(
            update={
                "escalation_reason": f"execution_error: {error_type}: {error_msg[:200]}",
                "react_attempts": intermediate_steps if 'intermediate_steps' in locals() else [],
                "react_thoughts": thoughts if 'thoughts' in locals() else [],  # Preserve thoughts if available
                "partial_result": f"Error occurred: {error_type}: {error_msg[:200]}",
                "goto": "planner"  # Set goto in state for conditional edge
            },
            goto="planner"
        )


async def pm_agent_node(
    state: State, config: RunnableConfig
) -> Command[Literal["research_team"]]:
    """
    Dedicated PM Agent node for project management queries.
    
    This agent ONLY has access to PM tools (no web search) and is specifically
    designed to retrieve and analyze data from the connected PM system.
    """
    logger.info(f"[DEBUG-NODES] [NODE-PM-AGENT-1] PM Agent node entered")
    import sys
    sys.stderr.write("\n🚨🚨🚨 PM_AGENT_NODE CALLED 🚨🚨🚨\n")
    sys.stderr.flush()
    logger.error("🚨🚨🚨 PM_AGENT_NODE CALLED - THIS SHOULD APPEAR IN LOGS! 🚨🚨🚨")
    logger.info("PM Agent node is analyzing project management data.")
    logger.debug(f"[pm_agent_node] Starting PM agent with PM tools only")
    
    # PM Agent has NO web search or code execution tools
    # It ONLY has access to PM tools which are loaded via MCP configuration
    # in _setup_and_execute_agent_step
    tools: list[Any] = []  # No additional tools - PM tools only via MCP
    
    logger.info(f"[pm_agent_node] PM Agent will use PM tools exclusively (loaded via MCP)")
    
    try:
        return await _setup_and_execute_agent_step(
            state,
            config,
            "pm_agent",
            tools,
        )
    except Exception as e:
        # Catch any unhandled exceptions to prevent workflow from getting stuck
        logger.error(
            f"[pm_agent_node] Unhandled exception: {e}",
            exc_info=True
        )
        
        # Handle error gracefully by marking step as failed
        error_message = f"[ERROR] PM Agent failed with unhandled exception: {str(e)}"
        
        current_plan = state.get("current_plan")
        if current_plan and not isinstance(current_plan, str) and hasattr(current_plan, 'steps'):
            from src.prompts.planner_model import Step, Plan
            
            # Find first incomplete step
            current_step_idx = None
            for idx, step in enumerate(current_plan.steps):
                if not step.execution_res:
                    current_step_idx = idx
                    break
            
            if current_step_idx is not None:
                # Mark step as failed
                updated_step = Step(
                    need_search=current_plan.steps[current_step_idx].need_search,
                    title=current_plan.steps[current_step_idx].title,
                    description=current_plan.steps[current_step_idx].description,
                    step_type=current_plan.steps[current_step_idx].step_type,
                    execution_res=error_message,
                )
                updated_steps = list(current_plan.steps)
                updated_steps[current_step_idx] = updated_step
                updated_plan = Plan(
                    locale=current_plan.locale,
                    has_enough_context=current_plan.has_enough_context,
                    thought=current_plan.thought,
                    title=current_plan.title,
                    steps=updated_steps,
                )
                
                # Check if all steps are done (including failed ones)
                all_done = all(step.execution_res for step in updated_plan.steps)
                return Command(
                    update={
                        "messages": [HumanMessage(content=error_message, name="pm_agent")],
                        "observations": state.get("observations", []) + [error_message],
                        "current_plan": updated_plan,
                    },
                    goto="reporter" if all_done else "research_team",
                )
        
        # Fallback: route to reporter with error
        return Command(
            update={
                "messages": [HumanMessage(content=error_message, name="pm_agent")],
                "observations": state.get("observations", []) + [error_message],
            },
            goto="reporter",
        )

        return Command(
            update={
                "messages": [HumanMessage(content=error_message, name="pm_agent")],
                "observations": state.get("observations", []) + [error_message],
            },
            goto="reporter",
        )
