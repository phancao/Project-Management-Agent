# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import json
import logging
import os
from functools import partial
from typing import Annotated, Literal
import re

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
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
from src.tools.analytics_tools import get_analytics_tools
from src.tools.pm_tools import get_pm_tools
from src.tools.search import LoggedTavilySearch
from src.utils.context_manager import ContextManager, validate_message_content
from src.utils.json_utils import repair_json_output, sanitize_tool_response

from ..config import SELECTED_SEARCH_ENGINE, SearchEngine
from .types import State
from .utils import (
    build_clarified_topic_from_history,
    get_message_content,
    is_user_message,
    reconstruct_clarification_history,
)

logger = logging.getLogger(__name__)


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
    research_topic: Annotated[str, "The topic of the research task to be handed off."],
    locale: Annotated[str, "The user's detected language locale (e.g., en-US, zh-CN)."],
):
    """Handoff to planner agent to do plan."""
    # This tool is not returning anything: we're just using it
    # as a way for LLM to signal that it needs to hand off to planner agent
    return


@tool
def handoff_after_clarification(
    locale: Annotated[str, "The user's detected language locale (e.g., en-US, zh-CN)."],
    research_topic: Annotated[
        str, "The clarified research topic based on all clarification rounds."
    ],
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
    # SECTION 2: Validate project analysis completeness
    # ============================================================
    # Check if this is a project analysis request
    plan_title = plan.get("title", "").lower()
    plan_thought = plan.get("thought", "").lower()
    is_project_analysis = (
        "project" in plan_title and "analysis" in plan_title
    ) or (
        "project" in plan_thought and "analysis" in plan_thought
    ) or any(
        "project" in step.get("title", "").lower() and "analysis" in step.get("title", "").lower()
        for step in steps
    )
    
    if is_project_analysis:
        # Required analytics tools for comprehensive project analysis
        required_tools = [
            "get_project",
            "project_health",
            "list_sprints",
            "list_tasks",
            "velocity_chart",
            "burndown_chart",
            "sprint_report",
            "cfd_chart",
            "cycle_time_chart",
            "work_distribution_chart",
            "issue_trend_chart"
        ]
        
        # Check all step descriptions for tool mentions
        all_descriptions = " ".join([
            step.get("description", "").lower() + " " + step.get("title", "").lower()
            for step in steps
        ])
        
        missing_tools = []
        for tool in required_tools:
            # Check if tool is mentioned (with variations)
            tool_variations = [
                tool,
                tool.replace("_", " "),
                tool.replace("_chart", ""),
                tool.replace("_", "-")
            ]
            if not any(variant in all_descriptions for variant in tool_variations):
                missing_tools.append(tool)
        
        if missing_tools:
            logger.warning(
                f"[VALIDATION] Project analysis plan missing {len(missing_tools)} required tools: {', '.join(missing_tools)}"
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
                        enhanced_desc = (
                            f"{current_desc}\n\n"
                            f"⚠️ MISSING TOOLS DETECTED: You must also call these tools: {missing_list}. "
                            f"Call ALL 11 tools: get_project, project_health, list_sprints, list_tasks, "
                            f"velocity_chart, burndown_chart, sprint_report, cfd_chart, cycle_time_chart, "
                            f"work_distribution_chart, issue_trend_chart."
                        )
                        step["description"] = enhanced_desc
                        logger.info(
                            f"[VALIDATION] Enhanced step '{step.get('title', 'N/A')}' description "
                            f"with missing tools reminder"
                        )
                    break

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
    background_investigation_results = []
    
    if SELECTED_SEARCH_ENGINE == SearchEngine.TAVILY.value:
        searched_content = LoggedTavilySearch(
            max_results=configurable.max_search_results
        ).invoke(query)
        # check if the searched_content is a tuple, then we need to unpack it
        if isinstance(searched_content, tuple):
            searched_content = searched_content[0]
        
        # Handle string JSON response (new format from fixed Tavily tool)
        if isinstance(searched_content, str):
            try:
                parsed = json.loads(searched_content)
                if isinstance(parsed, dict) and "error" in parsed:
                    logger.error(f"Tavily search error: {parsed['error']}")
                    background_investigation_results = []
                elif isinstance(parsed, list):
                    background_investigation_results = [
                        f"## {elem.get('title', 'Untitled')}\n\n{elem.get('content', 'No content')}" 
                        for elem in parsed
                    ]
                else:
                    logger.error(f"Unexpected Tavily response format: {searched_content}")
                    background_investigation_results = []
            except json.JSONDecodeError:
                logger.error(f"Failed to parse Tavily response as JSON: {searched_content}")
                background_investigation_results = []
        # Handle legacy list format
        elif isinstance(searched_content, list):
            background_investigation_results = [
                f"## {elem['title']}\n\n{elem['content']}" for elem in searched_content
            ]
            return {
                "background_investigation_results": "\n\n".join(
                    background_investigation_results
                )
            }
        else:
            logger.error(
                f"Tavily search returned malformed response: {searched_content}"
            )
            background_investigation_results = []
    else:
        background_investigation_results = get_web_search_tool(
            configurable.max_search_results
        ).invoke(query)
    
    return {
        "background_investigation_results": json.dumps(
            background_investigation_results, ensure_ascii=False
        )
    }


def planner_node(
    state: State, config: RunnableConfig
) -> Command[Literal["human_feedback", "reporter"]]:
    """Planner node that generate the full plan."""
    logger.info("Planner generating full plan")
    configurable = Configuration.from_runnable_config(config)
    plan_iterations = state["plan_iterations"] if state.get("plan_iterations", 0) else 0

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

    if configurable.enable_deep_thinking:
        llm = get_llm_by_type("reasoning")
    elif AGENT_LLM_MAP["planner"] == "basic":
        llm = get_llm_by_type("basic").with_structured_output(
            Plan,
            method="json_mode",
        )
    else:
        llm = get_llm_by_type(AGENT_LLM_MAP["planner"])

    # if the plan iterations is greater than the max plan iterations, return the reporter node
    if plan_iterations >= configurable.max_plan_iterations:
        return Command(goto="reporter")

    full_response = ""
    if AGENT_LLM_MAP["planner"] == "basic" and not configurable.enable_deep_thinking:
        try:
            response = llm.invoke(messages)
            full_response = response.model_dump_json(indent=4, exclude_none=True)
        except Exception as e:
            # If structured output validation fails, extract JSON from error message and fix it
            logger.error(f"[PLANNER] Structured output validation failed: {e}")
            error_str = str(e)
            # Try to extract JSON from error message (format: "Failed to parse Plan from completion {json}...")
            json_match = re.search(r'from completion\s+(\{.*?\})\s*\.', error_str, re.DOTALL)
            if json_match:
                try:
                    full_response = json_match.group(1)
                    logger.info(f"[PLANNER] Extracted JSON from error, will fix missing fields")
                except Exception:
                    logger.error(f"[PLANNER] Failed to extract JSON from error")
                    if plan_iterations > 0:
                        return Command(goto="reporter")
                    else:
                        return Command(goto="__end__")
            else:
                logger.error(f"[PLANNER] Could not extract JSON from error message")
                if plan_iterations > 0:
                    return Command(goto="reporter")
                else:
                    return Command(goto="__end__")
    else:
        response = llm.stream(messages)
        for chunk in response:
            full_response += chunk.content
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
) -> Command[Literal["planner", "background_investigator", "coordinator", "__end__"]]:
    """Coordinator node that communicate with customers and handle clarification."""
    logger.info("Coordinator talking.")
    configurable = Configuration.from_runnable_config(config)

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

        goto = "__end__"
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

                # Append coordinator's question to messages
                updated_messages = list(state_messages)
                if response.content:
                    updated_messages.append(
                        HumanMessage(content=response.content, name="coordinator")
                    )

                return Command(
                    update={
                        "messages": updated_messages,
                        "locale": locale,
                        "research_topic": research_topic,
                        "resources": configurable.resources,
                        "clarification_rounds": clarification_rounds,
                        "clarification_history": clarification_history,
                        "clarified_research_topic": clarified_topic,
                        "is_clarification_complete": False,
                        "goto": goto,
                        "__interrupt__": [("coordinator", response.content)],
                    },
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
    messages = list(state.get("messages", []) or [])
    if response.content:
        messages.append(HumanMessage(content=response.content, name="coordinator"))

    # Process tool calls for BOTH branches (legacy and clarification)
    if response.tool_calls:
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
        # Log full response for debugging
        logger.debug(f"Coordinator response content: {response.content}")
        logger.debug(f"Coordinator response object: {response}")
        # Fallback to planner to ensure workflow continues
        goto = "planner"

    # Apply background_investigation routing if enabled (unified logic)
    if goto == "planner" and state.get("enable_background_investigation"):
        goto = "background_investigator"

    # Set default values for state variables (in case they're not defined in legacy mode)
    if not enable_clarification:
        clarification_rounds = 0
        clarification_history = []

    clarified_research_topic_value = clarified_topic or research_topic

    # clarified_research_topic: Complete clarified topic with all clarification rounds
    return Command(
        update={
            "messages": messages,
            "locale": locale,
            "research_topic": research_topic,
            "clarified_research_topic": clarified_research_topic_value,
            "resources": configurable.resources,
            "clarification_rounds": clarification_rounds,
            "clarification_history": clarification_history,
            "is_clarification_complete": goto != "coordinator",
            "goto": goto,
        },
        goto=goto,
    )


def reporter_node(state: State, config: RunnableConfig):
    """Reporter node that write a final report."""
    logger.info("Reporter write final report")
    configurable = Configuration.from_runnable_config(config)
    current_plan = state.get("current_plan")
    
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
    
    input_ = {
        "messages": [
            HumanMessage(
                f"# Research Requirements\n\n## Task\n\n{plan_title}\n\n## Description\n\n{plan_thought}"
            )
        ],
        "locale": state.get("locale", "en-US"),
    }
    invoke_messages = apply_prompt_template("reporter", input_, configurable, input_.get("locale", "en-US"))
    observations = state.get("observations", [])
    
    # CRITICAL: Also collect observations from all completed steps
    # This ensures we get data even if observations state is incomplete
    if current_plan and not isinstance(current_plan, str) and hasattr(current_plan, 'steps') and current_plan.steps:
        step_observations = []
        for idx, step in enumerate(current_plan.steps):
            if step.execution_res:
                # Include step title for context
                step_obs = f"## Step {idx + 1}: {step.title}\n\n{step.execution_res}"
                step_observations.append(step_obs)
                logger.debug(f"Reporter: Collected observation from step {idx + 1}: {step.title}")
        
        # Combine state observations with step observations
        # Use step observations if they exist and are more complete
        if step_observations:
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

    # Add a reminder about the new report format, citation style, and table usage
    invoke_messages.append(
        HumanMessage(
            content="IMPORTANT: Structure your report according to the format in the prompt. Remember to include:\n\n1. Key Points - A bulleted list of the most important findings\n2. Overview - A brief introduction to the topic\n3. Detailed Analysis - Organized into logical sections\n4. Survey Note (optional) - For more comprehensive reports\n5. Key Citations - List all references at the end\n\nFor citations, DO NOT include inline citations in the text. Instead, place all citations in the 'Key Citations' section at the end using the format: `- [Source Title](URL)`. Include an empty line between each citation for better readability.\n\nPRIORITIZE USING MARKDOWN TABLES for data presentation and comparison. Use tables whenever presenting comparative data, statistics, features, or options. Structure tables with clear headers and aligned columns. Example table format:\n\n| Feature | Description | Pros | Cons |\n|---------|-------------|------|------|\n| Feature 1 | Description 1 | Pros 1 | Cons 1 |\n| Feature 2 | Description 2 | Pros 2 | Cons 2 |",
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

    # Context compression
    llm_token_limit = get_llm_token_limit_by_type(AGENT_LLM_MAP["reporter"])
    compressed_state = ContextManager(llm_token_limit).compress_messages(
        {"messages": observation_messages}
    )
    compressed_messages = compressed_state.get("messages", [])
    
    # Log compression results for debugging
    if len(compressed_messages) != len(observation_messages):
        logger.warning(
            f"Reporter: Observations compressed from {len(observation_messages)} to {len(compressed_messages)} messages"
        )
    
    invoke_messages += compressed_messages

    logger.debug(f"Current invoke messages: {invoke_messages}")
    response = get_llm_by_type(AGENT_LLM_MAP["reporter"]).invoke(invoke_messages)
    response_content = response.content
    logger.info(f"reporter response: {response_content}")

    # Create AIMessage with finish_reason in response_metadata
    # This ensures the frontend knows the message is complete
    reporter_message = AIMessage(
        content=response_content,
        name="reporter",
        response_metadata={"finish_reason": "stop"}
    )

    # Add AIMessage so the final report gets streamed to the client
    return {
        "messages": [reporter_message],
        "final_report": response_content,
    }


def research_team_node(state: State):
    """Research team node that collaborates on tasks."""
    logger.info("Research team is collaborating on tasks.")
    logger.debug("Entering research_team_node - coordinating research and coder agents")
    pass


async def _execute_agent_step(
    state: State, agent, agent_name: str
) -> Command[Literal["research_team"]]:
    """Helper function to execute a step using the specified agent."""
    import sys
    sys.stderr.write(f"\n⚡ EXECUTE_AGENT_STEP: agent_name='{agent_name}'\n")
    sys.stderr.flush()
    
    logger.debug(f"[_execute_agent_step] Starting execution for agent: {agent_name}")
    
    current_plan = state.get("current_plan")
    plan_title = current_plan.title
    observations = state.get("observations", [])
    
    import sys
    sys.stderr.write(f"\n📋 PLAN INFO: plan_title='{plan_title}'\n")
    sys.stderr.flush()
    
    logger.debug(f"[_execute_agent_step] Plan title: {plan_title}, observations count: {len(observations)}")

    # Find the first unexecuted step
    current_step = None
    completed_steps = []
    for idx, step in enumerate(current_plan.steps):
        if not step.execution_res:
            current_step = step
            logger.debug(f"[_execute_agent_step] Found unexecuted step at index {idx}: {step.title}")
            break
        else:
            completed_steps.append(step)

    if not current_step:
        logger.warning(f"[_execute_agent_step] No unexecuted step found in {len(current_plan.steps)} total steps")
        return Command(goto="research_team")

    logger.info(f"[_execute_agent_step] Executing step: {current_step.title}, agent: {agent_name}")
    logger.debug(f"[_execute_agent_step] Completed steps so far: {len(completed_steps)}")

    # Format completed steps information
    completed_steps_info = ""
    if completed_steps:
        completed_steps_info = "# Completed Research Steps\n\n"
        for i, step in enumerate(completed_steps):
            completed_steps_info += f"## Completed Step {i + 1}: {step.title}\n\n"
            completed_steps_info += f"<finding>\n{step.execution_res}\n</finding>\n\n"

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
        if state.get("resources"):
            resources_info = "**The user mentioned the following resource files:**\n\n"
            for resource in state.get("resources"):
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
    import sys
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

    import sys
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
        validated_messages = validate_message_content(agent_input["messages"])
        agent_input["messages"] = validated_messages
    except Exception as validation_error:
        logger.error(f"Error validating agent input messages: {validation_error}")
    
    try:
        result = await agent.ainvoke(
            input=agent_input, config={"recursion_limit": recursion_limit}
        )
        
        import sys
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
        import sys
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
        current_step.execution_res = detailed_error

        # Calculate the current step index even on error
        completed_count = sum(1 for step in current_plan.steps if step.execution_res)
        current_step_index = min(completed_count, len(current_plan.steps) - 1)

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
            },
            goto="research_team",
        )

    # Process the result
    response_content = result["messages"][-1].content
    
    # Log all messages to debug tool call results
    logger.debug(f"[{agent_name}] All messages in result: {len(result.get('messages', []))}")
    for i, msg in enumerate(result.get("messages", [])):
        msg_type = type(msg).__name__
        if msg_type == "ToolMessage":
            logger.info(f"[{agent_name}] Message {i}: ToolMessage - tool_call_id={getattr(msg, 'tool_call_id', 'N/A')}, content={str(msg.content)[:200]}")
        elif msg_type == "AIMessage":
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                logger.info(f"[{agent_name}] Message {i}: AIMessage with {len(msg.tool_calls)} tool calls: {[tc.get('name', 'N/A') for tc in msg.tool_calls]}")
            else:
                logger.debug(f"[{agent_name}] Message {i}: AIMessage - content={str(msg.content)[:200]}")
        else:
            logger.debug(f"[{agent_name}] Message {i}: {msg_type} - content={str(msg.content)[:200] if hasattr(msg, 'content') else 'N/A'}")
    
    # Sanitize response to remove extra tokens and truncate if needed
    response_content = sanitize_tool_response(str(response_content))
    
    logger.debug(f"{agent_name.capitalize()} full response: {response_content}")

    # Update the step with the execution result
    current_step.execution_res = response_content
    logger.info(f"Step '{current_step.title}' execution completed by {agent_name}")

    # Calculate the current step index (number of completed steps)
    completed_count = sum(1 for step in current_plan.steps if step.execution_res)
    current_step_index = min(completed_count, len(current_plan.steps) - 1)
    logger.info(f"Step progress: {completed_count}/{len(current_plan.steps)} steps completed (current_step_index={current_step_index})")

    import sys
    from langchain_core.messages import AIMessage
    sys.stderr.write(f"\n🔄 RETURNING RESULT: agent_name='{agent_name}', message_type='AIMessage', content_len={len(response_content)}\n")
    sys.stderr.flush()
    
    return Command(
        update={
            "messages": [
                AIMessage(
                    content=response_content,
                    name=agent_name,
                )
            ],
            "observations": observations + [response_content],
            "current_step_index": current_step_index,  # Update step progress
        },
        goto="research_team",
    )


async def _setup_and_execute_agent_step(
    state: State,
    config: RunnableConfig,
    agent_type: str,
    default_tools: list,
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
            client = MultiServerMCPClient(mcp_servers)
            logger.info(f"[{agent_type}] MultiServerMCPClient created. Checking connections...")
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
            logger.info(f"[{agent_type}] Calling client.get_tools()...")
            all_tools = await client.get_tools()
            logger.info(
                f"[{agent_type}] Retrieved {len(all_tools)} tools from MCP servers"
            )
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
                    loaded_tools.append(tool)
                    added_count += 1
                    if tool.name == "list_my_tasks":
                        list_my_tasks_added = True
                    logger.info(
                        f"[{agent_type}] Added MCP tool: {tool.name} "
                        f"(from {server_name})"
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
            # CRITICAL: Do NOT fall back to default tools - this causes AI to hallucinate data
            # Instead, raise an error so the user knows PM tools aren't available
            raise RuntimeError(
                f"Failed to load PM tools from MCP server: {e}. "
                "Cannot proceed without PM tools as this would cause AI to generate fake data. "
                "Please ensure the MCP server is running and accessible."
            )

        llm_token_limit = get_llm_token_limit_by_type(AGENT_LLM_MAP[agent_type])
        pre_model_hook = partial(ContextManager(llm_token_limit, 3).compress_messages)
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
        llm_token_limit = get_llm_token_limit_by_type(AGENT_LLM_MAP[agent_type])
        pre_model_hook = partial(ContextManager(llm_token_limit, 3).compress_messages)
        agent = create_agent(
            agent_type,
            agent_type,
            default_tools,
            agent_type,
            pre_model_hook,
            interrupt_before_tools=configurable.interrupt_before_tools,
        )
        return await _execute_agent_step(state, agent, agent_type)


async def researcher_node(
    state: State, config: RunnableConfig
) -> Command[Literal["research_team"]]:
    """Researcher node that do research"""
    logger.info("Researcher node is researching.")
    logger.debug(f"[researcher_node] Starting researcher agent")
    
    configurable = Configuration.from_runnable_config(config)
    logger.debug(f"[researcher_node] Max search results: {configurable.max_search_results}")
    
    tools = [get_web_search_tool(configurable.max_search_results), crawl_tool, backend_api_call]
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


async def pm_agent_node(
    state: State, config: RunnableConfig
) -> Command[Literal["research_team"]]:
    """
    Dedicated PM Agent node for project management queries.
    
    This agent ONLY has access to PM tools (no web search) and is specifically
    designed to retrieve and analyze data from the connected PM system.
    """
    import sys
    sys.stderr.write("\n🚨🚨🚨 PM_AGENT_NODE CALLED 🚨🚨🚨\n")
    sys.stderr.flush()
    logger.error("🚨🚨🚨 PM_AGENT_NODE CALLED - THIS SHOULD APPEAR IN LOGS! 🚨🚨🚨")
    logger.info("PM Agent node is analyzing project management data.")
    logger.debug(f"[pm_agent_node] Starting PM agent with PM tools only")
    
    # PM Agent has NO web search or code execution tools
    # It ONLY has access to PM tools which are loaded via MCP configuration
    # in _setup_and_execute_agent_step
    tools = []  # No additional tools - PM tools only via MCP
    
    logger.info(f"[pm_agent_node] PM Agent will use PM tools exclusively (loaded via MCP)")
    
    return await _setup_and_execute_agent_step(
        state,
        config,
        "pm_agent",
        tools,
    )
