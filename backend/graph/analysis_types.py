"""
Analysis Type Configuration

Maps different PM analysis types to their required tools.
This allows flexible validation without hardcoding rules.
"""

from typing import Dict, List, Set, Optional
from enum import Enum


class AnalysisType(str, Enum):
    """Types of PM analysis queries."""
    PROJECT = "project"
    SPRINT = "sprint"
    EPIC = "epic"
    MILESTONE = "milestone"
    RESOURCE = "resource"
    USER = "user"
    TASK = "task"
    UNKNOWN = "unknown"


# Map analysis types to their required tools
ANALYSIS_TOOL_REQUIREMENTS: Dict[AnalysisType, List[str]] = {
    AnalysisType.PROJECT: [
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
        "issue_trend_chart",
    ],
    AnalysisType.SPRINT: [
        "list_sprints",  # To find sprint_id
        "sprint_report",
        "burndown_chart",
        "list_tasks",
    ],
    AnalysisType.EPIC: [
        "list_epics",
        "list_tasks",  # Tasks in epic
        "get_epic",  # If available
    ],
    AnalysisType.MILESTONE: [
        "list_tasks",  # Tasks related to milestone
        "list_sprints",  # Sprints related to milestone
    ],
    AnalysisType.RESOURCE: [
        "list_users",
        "work_distribution_chart",  # By assignee dimension - returns aggregated data, not individual tasks
        # NOTE: DO NOT use list_tasks for resource analysis - it returns 100+ tasks causing token overflow
        # Use work_distribution_chart instead which returns aggregated counts/percentages
    ],
    AnalysisType.USER: [
        "list_users",
        "list_tasks",  # Tasks assigned to user
    ],
    AnalysisType.TASK: [
        "list_tasks",
        "get_task",  # If specific task
    ],
    AnalysisType.UNKNOWN: [],  # No requirements for unknown types
}


# Keywords to detect analysis types
ANALYSIS_TYPE_KEYWORDS: Dict[AnalysisType, List[str]] = {
    AnalysisType.PROJECT: [
        "project analysis",
        "project overview",
        "project status",
        "project health",
        "comprehensive analysis",
        "full analysis",
        "analyze project",
        "analyse project",
    ],
    AnalysisType.SPRINT: [
        "sprint analysis",
        "sprint performance",
        "sprint report",
        "sprint metrics",
        "analyze sprint",
        "analyse sprint",
        "sprint [number]",  # Pattern: sprint 4, sprint 5, etc.
    ],
    AnalysisType.EPIC: [
        "epic analysis",
        "epic progress",
        "epic status",
        "epic report",
        "analyze epic",
        "analyse epic",
    ],
    AnalysisType.MILESTONE: [
        "milestone analysis",
        "milestone progress",
        "milestone status",
        "analyze milestone",
        "analyse milestone",
    ],
    AnalysisType.RESOURCE: [
        "resource analysis",
        "resource allocation",
        "resource assignation",
        "team workload",
        "workload analysis",
        "resource utilization",
        "analyze resource",
        "analyse resource",
    ],
    AnalysisType.USER: [
        "user analysis",
        "team member analysis",
        "assignee analysis",
    ],
    AnalysisType.TASK: [
        "task analysis",
        "task progress",
        "task status",
    ],
}


def detect_analysis_type(
    plan_title: str,
    plan_thought: str,
    step_titles: List[str],
    step_descriptions: List[str],
) -> AnalysisType:
    """
    Detect the analysis type from plan content.
    
    Args:
        plan_title: Plan title
        plan_thought: Plan thought/description
        step_titles: List of step titles
        step_descriptions: List of step descriptions
    
    Returns:
        Detected AnalysisType
    """
    # Combine all text for analysis
    all_text = " ".join([
        plan_title.lower(),
        plan_thought.lower(),
        *[t.lower() for t in step_titles],
        *[d.lower() for d in step_descriptions],
    ])
    
    # Check for sprint-specific patterns first (most specific)
    # Pattern: "sprint [number]" or "sprint [name]" with analysis keywords
    import re
    sprint_pattern = r"sprint\s+(\d+|[a-zA-Z]+)"
    if re.search(sprint_pattern, all_text):
        analysis_keywords = ["analysis", "performance", "report", "metrics", "analyze", "analyse"]
        if any(keyword in all_text for keyword in analysis_keywords):
            # Make sure it's not "project analysis" that happens to mention sprint
            if "project" in all_text and "analysis" in all_text:
                # Check if "project analysis" appears before sprint mention
                project_analysis_pos = all_text.find("project")
                sprint_pos = all_text.find("sprint")
                if project_analysis_pos < sprint_pos:
                    return AnalysisType.PROJECT
            return AnalysisType.SPRINT
    
    # Check other analysis types (in order of specificity)
    for analysis_type, keywords in ANALYSIS_TYPE_KEYWORDS.items():
        if analysis_type == AnalysisType.SPRINT:
            continue  # Already checked above
        
        for keyword in keywords:
            # Handle pattern keywords like "sprint [number]"
            if "[number]" in keyword:
                pattern = keyword.replace("[number]", r"\d+")
                if re.search(pattern, all_text):
                    return analysis_type
            elif keyword in all_text:
                return analysis_type
    
    # Default to UNKNOWN if no match
    return AnalysisType.UNKNOWN


def get_required_tools(analysis_type: AnalysisType) -> List[str]:
    """
    Get required tools for an analysis type.
    
    Args:
        analysis_type: The analysis type
    
    Returns:
        List of required tool names
    """
    return ANALYSIS_TOOL_REQUIREMENTS.get(analysis_type, [])


def validate_analysis_plan(
    plan: Dict,
    steps: List[Dict],
) -> tuple[bool, Optional[AnalysisType], List[str]]:
    """
    Validate an analysis plan against its detected analysis type.
    
    Args:
        plan: Plan dictionary
        steps: List of step dictionaries
    
    Returns:
        Tuple of (is_valid, analysis_type, missing_tools)
    """
    plan_title = plan.get("title", "")
    plan_thought = plan.get("thought", "")
    step_titles = [step.get("title", "") for step in steps]
    step_descriptions = [step.get("description", "") for step in steps]
    
    # Detect analysis type
    analysis_type = detect_analysis_type(
        plan_title,
        plan_thought,
        step_titles,
        step_descriptions,
    )
    
    # If unknown or no requirements, skip validation
    if analysis_type == AnalysisType.UNKNOWN:
        return True, analysis_type, []
    
    # Get required tools for this analysis type
    required_tools = get_required_tools(analysis_type)
    if not required_tools:
        return True, analysis_type, []  # No requirements = always valid
    
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
            tool.replace("_", "-"),
        ]
        if not any(variant in all_descriptions for variant in tool_variations):
            missing_tools.append(tool)
    
    is_valid = len(missing_tools) == 0
    return is_valid, analysis_type, missing_tools

