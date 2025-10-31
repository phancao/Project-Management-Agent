# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class PMStepType(str, Enum):
    """Project Management step types"""
    CREATE_PROJECT = "create_project"
    CREATE_WBS = "create_wbs"
    SPRINT_PLANNING = "sprint_planning"
    TASK_ASSIGNMENT = "task_assignment"
    RESEARCH = "research"
    CREATE_REPORT = "create_report"
    GANTT_CHART = "gantt_chart"
    DEPENDENCY_ANALYSIS = "dependency_analysis"
    UNKNOWN = "unknown"


class PMStep(BaseModel):
    """A single step in a project management plan"""
    step_type: PMStepType = Field(..., description="Type of PM task to execute")
    title: str = Field(..., description="Short title describing the step")
    description: str = Field(..., description="Detailed description of what to do")
    requires_context: bool = Field(
        default=True, 
        description="Whether this step needs context from previous steps"
    )
    execution_res: Optional[str] = Field(
        default=None, 
        description="Execution result after completion"
    )


class PMPlan(BaseModel):
    """Project Management execution plan"""
    locale: str = Field(
        ..., 
        description="e.g. 'en-US' or 'vi-VN', based on user's language"
    )
    overall_thought: str = Field(
        ..., 
        description="Overall approach and reasoning"
    )
    steps: List[PMStep] = Field(
        default_factory=list,
        description="Sequential steps to execute"
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "locale": "en-US",
                    "overall_thought": "I will create a comprehensive WBS first, then plan two sprints based on task priorities and capacity.",
                    "steps": [
                        {
                            "step_type": "create_wbs",
                            "title": "Create WBS for QA Automation Project",
                            "description": "Generate a detailed Work Breakdown Structure with phases, deliverables, and tasks",
                            "requires_context": False
                        },
                        {
                            "step_type": "sprint_planning",
                            "title": "Plan Sprint 1",
                            "description": "Create first 2-week sprint with task assignments",
                            "requires_context": True
                        },
                        {
                            "step_type": "sprint_planning",
                            "title": "Plan Sprint 2",
                            "description": "Create second 2-week sprint with remaining tasks",
                            "requires_context": True
                        }
                    ]
                }
            ]
        }
