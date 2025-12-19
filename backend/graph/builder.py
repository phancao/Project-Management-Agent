# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from backend.prompts.planner_model import StepType

from .nodes import (
    background_investigation_node,
    coder_node,
    coordinator_node,
    human_feedback_node,
    planner_node,
    pm_agent_node,
    react_agent_node,
    reflection_node as reflector_node,
    reporter_node,
    research_team_node,
    researcher_node,
    validator_node,
)
from .types import State


def continue_to_running_research_team(state: State):
    current_plan = state.get("current_plan")
    if not current_plan:
        return "planner"

    # Handle case where current_plan might be a string (legacy)
    if isinstance(current_plan, str):
        return "planner"
    
    if not current_plan.steps:
        return "planner"

    # Check if all steps have execution_res (completed or failed)
    if all(step.execution_res for step in current_plan.steps):
        # All steps completed (or failed)
        # CRITICAL: Check if we already have a final_report (reporter already completed)
        # If reporter already completed, route directly to END to prevent duplicate reporter calls
        if state.get("final_report"):
            import logging
            logger = logging.getLogger(__name__)
            logger.info("All steps complete and reporter already finished. Routing directly to END.")
            # CRITICAL FIX: Route directly to END, not validator
            # This prevents the validator from routing to reporter again
            return "__end__"
        # Route to validator - it will validate and route to reporter
        # This prevents duplicate reporter invocations
        return "validator"

    # Find first incomplete step (no execution_res)
    incomplete_step = None
    incomplete_step_idx = None
    for idx, step in enumerate(current_plan.steps):
        if not step.execution_res:
            incomplete_step = step
            incomplete_step_idx = idx
            break

    if not incomplete_step:
        # No incomplete step found but also not all completed?
        # This shouldn't happen, route to validator
        return "validator"
    
    # Check if this step has been retried too many times (prevent infinite loops)
    # Count how many steps before this one have execution_res
    completed_before = sum(1 for step in current_plan.steps[:incomplete_step_idx] if step.execution_res)
    # If we've been stuck on the same step (no progress), route to reporter after 3 attempts
    current_step_index = state.get("current_step_index", 0)
    if completed_before == current_step_index and current_step_index >= 3:
        # We've been stuck - route to reporter to finish with what we have
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            f"Workflow appears stuck at step {incomplete_step_idx} ({incomplete_step.title}). "
            "Routing to reporter to finish analysis."
        )
        return "reporter"

    if incomplete_step.step_type == StepType.RESEARCH:
        return "researcher"
    if incomplete_step.step_type == StepType.PROCESSING:
        return "coder"
    if incomplete_step.step_type == StepType.PM_QUERY:
        return "pm_agent"
    return "planner"


def _build_base_graph():
    """Build and return the base state graph with all nodes and edges."""
    builder = StateGraph(State)
    
    # Add all nodes
    builder.add_node("coordinator", coordinator_node)
    builder.add_node("background_investigator", background_investigation_node)
    builder.add_node("planner", planner_node)
    builder.add_node("reporter", reporter_node)
    builder.add_node("research_team", research_team_node)
    builder.add_node("researcher", researcher_node)
    builder.add_node("coder", coder_node)
    builder.add_node("pm_agent", pm_agent_node)
    builder.add_node("human_feedback", human_feedback_node)
    
    # ADAPTIVE: Add ReAct agent for fast path
    builder.add_node("react_agent", react_agent_node)
    
    # Autonomous loop nodes
    builder.add_node("validator", validator_node)
    builder.add_node("reflector", reflector_node)
    
    # Entry point
    import logging
    logger = logging.getLogger(__name__)
    logger.info("[GRAPH-BUILDER] 🔧 Setting entry point: START → coordinator")
    builder.add_edge(START, "coordinator")
    logger.info("[GRAPH-BUILDER] ✅ Entry point configured: START → coordinator")
    
    # Background investigation always routes to planner
    builder.add_edge("background_investigator", "planner")
    
    # KEY CHANGE: After agent execution, route to validator instead of directly back to research_team
    builder.add_edge("pm_agent", "validator")
    builder.add_edge("researcher", "validator")
    builder.add_edge("coder", "validator")
    
    # Validator routes based on validation result
    def route_from_validator(state):
        goto = state.get("goto", "research_team")
        # Check if reporter already completed (prevent infinite loop)
        if state.get("final_report"):
            # Reporter already completed, route to END
            return "__end__"
        # Validator can only route to these nodes, map anything else to research_team
        allowed = ["research_team", "reflector", "reporter", "__end__"]
        if goto not in allowed:
            return "research_team"
        return goto
    
    builder.add_conditional_edges(
        "validator",
        route_from_validator,
        ["research_team", "reflector", "reporter", "__end__"]
    )
    
    # Reflector routes back to planner for replanning
    builder.add_edge("reflector", "planner")
    
    # Research team routes to agents or validator
    # When all steps are complete, research_team routes to validator
    # Validator will then route to reporter (prevents duplicate reporter invocations)
    builder.add_conditional_edges(
        "research_team",
        continue_to_running_research_team,
        ["planner", "researcher", "coder", "pm_agent", "validator", "__end__"],  # Added __end__ to allow direct routing to END
    )
    
    # Reporter is terminal
    builder.add_edge("reporter", END)
    
    # ReAct agent routes to planner (escalation) or reporter (success)
    builder.add_conditional_edges(
        "react_agent",
        lambda state: state.get("goto", "reporter"),
        ["planner", "reporter"]
    )
    
    # Coordinator handles clarification flow + adaptive routing  
    builder.add_conditional_edges(
        "coordinator",
        lambda state: state.get("goto", "react_agent"),
        ["planner", "background_investigator", "coordinator", "react_agent", END]
    )
    
    return builder


def build_graph_with_memory():
    """Build and return the agent workflow graph with memory."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("[GRAPH-BUILDER] 🏗️ Building graph with memory...")
    # use persistent memory to save conversation history
    # TODO: be compatible with SQLite / PostgreSQL
    memory = MemorySaver()

    # build state graph
    builder = _build_base_graph()
    compiled_graph = builder.compile(checkpointer=memory)
    logger.info("[GRAPH-BUILDER] ✅ Graph compiled successfully with entry point: START → coordinator")
    return compiled_graph


def build_graph():
    """Build and return the agent workflow graph without memory."""
    # build state graph
    builder = _build_base_graph()
    return builder.compile()


graph = build_graph()
