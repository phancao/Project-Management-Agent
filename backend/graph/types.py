# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT


from dataclasses import field

from langgraph.graph import MessagesState

from backend.prompts.planner_model import Plan
from backend.rag import Resource


class State(MessagesState):
    """State for the agent system, extends MessagesState with next field."""

    # Runtime Variables
    locale: str = "en-US"
    research_topic: str = ""
    clarified_research_topic: str = (
        ""  # Complete/final clarified topic with all clarification rounds
    )
    observations: list[str] = []
    resources: list[Resource] = []
    plan_iterations: int = 0
    current_plan: Plan | str = None
    current_step_index: int = 0  # Track which step is currently being executed (0-based)
    total_steps: int = 0  # Total number of steps in the plan
    final_report: str = ""
    auto_accepted_plan: bool = False
    enable_background_investigation: bool = True
    background_investigation_results: str = None
    project_id: str = ""  # PM project ID for PM Agent queries

    # Clarification state tracking (disabled by default)
    enable_clarification: bool = (
        False  # Enable/disable clarification feature (default: False)
    )
    clarification_rounds: int = 0
    clarification_history: list[str] = field(default_factory=list)
    is_clarification_complete: bool = False
    max_clarification_rounds: int = (
        3  # Default: 3 rounds (only used when enable_clarification=True)
    )

    # Autonomous loop state (validation and reflection)
    validation_results: list[dict] = field(default_factory=list)  # Results from validator node
    reflection: str = ""  # Reflection on failures for replanning
    retry_count: int = 0  # Number of retries for current step
    replan_reason: str = ""  # Reason for replanning
    max_replan_iterations: int = 3  # Maximum number of replanning attempts

    # Adaptive routing state
    routing_mode: str = ""  # "react_first", "user_escalated", "auto_escalated", etc.
    previous_result: str = ""
    
    # Token budget coordination (for frontend + backend context sharing)
    frontend_history_message_count: int = 0  # Number of messages from frontend history  # Store previous ReAct result for user feedback detection
    escalation_reason: str = ""  # Why was query escalated
    escalation_context: str = ""  # Context for escalated planning
    pm_report_type: str = "general" # PM Report Type (list, sprint, person, resources, etc.)
    react_intermediate_steps: list = field(default_factory=list)  # ReAct execution steps
    react_thoughts: list = field(default_factory=list)  # ReAct thoughts for UI display (streamed separately)

    # Workflow control
    goto: str = "planner"  # Default next node
