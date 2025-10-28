"""
Project Management Agent Manager
Orchestrates specialized agents for project management tasks
"""

import asyncio
import json
import os
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import openai
from datetime import datetime

from src.utils.logger import get_logger
from src.utils.config import get_config
from src.utils.errors import ProjectManagementError, APIError


logger = get_logger(__name__)


class AgentType(Enum):
    """Types of project management agents"""
    PROJECT_PLANNER = "project_planner"
    TASK_MANAGER = "task_manager"
    TEAM_COORDINATOR = "team_coordinator"
    RISK_ASSESSOR = "risk_assessor"
    PROGRESS_TRACKER = "progress_tracker"
    RESOURCE_OPTIMIZER = "resource_optimizer"
    COMMUNICATION_MANAGER = "communication_manager"


@dataclass
class AgentCapability:
    """Defines what an agent can do"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    tools: List[str]


@dataclass
class AgentContext:
    """Context information for agent execution"""
    user_id: str
    project_id: Optional[str] = None
    session_id: str = ""
    conversation_history: List[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = []
        if self.metadata is None:
            self.metadata = {}


class ProjectManagementAgent:
    """Base class for project management agents"""
    
    def __init__(
        self,
        agent_type: AgentType,
        capability: AgentCapability,
        system_prompt: str,
        tools: List[Callable] = None
    ):
        self.agent_type = agent_type
        self.capability = capability
        self.system_prompt = system_prompt
        self.tools = tools or []
        self.config = get_config()
        
        # Get API key from environment or config
        api_key = os.getenv('LLM_API_KEY') or self.config.llm.api_key
        if not api_key:
            raise ValueError("OpenAI API key not found. Set LLM_API_KEY environment variable.")
        
        self.client = openai.AsyncOpenAI(api_key=api_key)
        
    async def execute(
        self,
        user_input: str,
        context: AgentContext
    ) -> Dict[str, Any]:
        """
        Execute agent with user input and context
        
        Args:
            user_input: User's input message
            context: Agent execution context
            
        Returns:
            Agent response with action and data
        """
        try:
            # Prepare messages for OpenAI
            messages = self._prepare_messages(user_input, context)
            
            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=self.config.llm.model,
                messages=messages,
                temperature=self.config.llm.temperature,
                max_tokens=self.config.llm.max_tokens,
                tools=self._prepare_tools() if self.tools else None,
                tool_choice="auto" if self.tools else None
            )
            
            # Process response
            result = await self._process_response(response, context)
            
            logger.info(f"Agent {self.agent_type.value} executed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Agent {self.agent_type.value} execution failed: {e}")
            raise APIError(f"Agent execution failed: {str(e)}")
    
    def _prepare_messages(self, user_input: str, context: AgentContext) -> List[Dict[str, str]]:
        """Prepare messages for OpenAI API"""
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        # Add conversation history
        for msg in context.conversation_history[-10:]:  # Last 10 messages
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        
        # Add current user input
        messages.append({
            "role": "user",
            "content": user_input
        })
        
        return messages
    
    def _prepare_tools(self) -> List[Dict[str, Any]]:
        """Prepare tools for OpenAI API"""
        tools = []
        for tool in self.tools:
            if hasattr(tool, '__name__'):
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.__name__,
                        "description": tool.__doc__ or f"Tool: {tool.__name__}",
                        "parameters": self._get_tool_schema(tool)
                    }
                })
        return tools
    
    def _get_tool_schema(self, tool: Callable) -> Dict[str, Any]:
        """Get schema for tool function"""
        # This would be implemented based on tool introspection
        # For now, return a basic schema
        return {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "Input for the tool"
                }
            },
            "required": ["input"]
        }
    
    async def _process_response(
        self,
        response: Any,
        context: AgentContext
    ) -> Dict[str, Any]:
        """Process OpenAI response and execute tools if needed"""
        message = response.choices[0].message
        
        result = {
            "agent_type": self.agent_type.value,
            "response": message.content,
            "timestamp": datetime.now().isoformat(),
            "context": {
                "user_id": context.user_id,
                "project_id": context.project_id,
                "session_id": context.session_id
            }
        }
        
        # Handle tool calls
        if message.tool_calls:
            tool_results = []
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                # Find and execute tool
                tool_func = next(
                    (tool for tool in self.tools if tool.__name__ == tool_name),
                    None
                )
                
                if tool_func:
                    try:
                        tool_result = await tool_func(**tool_args)
                        tool_results.append({
                            "tool": tool_name,
                            "result": tool_result,
                            "success": True
                        })
                    except Exception as e:
                        tool_results.append({
                            "tool": tool_name,
                            "error": str(e),
                            "success": False
                        })
                else:
                    tool_results.append({
                        "tool": tool_name,
                        "error": f"Tool {tool_name} not found",
                        "success": False
                    })
            
            result["tool_results"] = tool_results
        
        return result


class ProjectManagementAgentManager:
    """Manages all project management agents"""
    
    def __init__(self):
        self.agents: Dict[AgentType, ProjectManagementAgent] = {}
        self.config = get_config()
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize all project management agents"""
        # Project Planner Agent
        self.agents[AgentType.PROJECT_PLANNER] = ProjectManagementAgent(
            agent_type=AgentType.PROJECT_PLANNER,
            capability=AgentCapability(
                name="Project Planning",
                description="Creates and manages project plans, timelines, and milestones",
                input_schema={
                    "type": "object",
                    "properties": {
                        "project_description": {"type": "string"},
                        "requirements": {"type": "array", "items": {"type": "string"}},
                        "constraints": {"type": "object"}
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "project_plan": {"type": "object"},
                        "timeline": {"type": "array"},
                        "milestones": {"type": "array"}
                    }
                },
                tools=["create_project", "update_timeline", "add_milestone"]
            ),
            system_prompt=self._get_project_planner_prompt()
        )
        
        # Task Manager Agent
        self.agents[AgentType.TASK_MANAGER] = ProjectManagementAgent(
            agent_type=AgentType.TASK_MANAGER,
            capability=AgentCapability(
                name="Task Management",
                description="Manages individual tasks, assignments, and dependencies",
                input_schema={
                    "type": "object",
                    "properties": {
                        "task_description": {"type": "string"},
                        "assignee": {"type": "string"},
                        "priority": {"type": "string"},
                        "deadline": {"type": "string"}
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string"},
                        "status": {"type": "string"},
                        "assignee": {"type": "string"}
                    }
                },
                tools=["create_task", "assign_task", "update_status", "set_priority"]
            ),
            system_prompt=self._get_task_manager_prompt()
        )
        
        # Team Coordinator Agent
        self.agents[AgentType.TEAM_COORDINATOR] = ProjectManagementAgent(
            agent_type=AgentType.TEAM_COORDINATOR,
            capability=AgentCapability(
                name="Team Coordination",
                description="Coordinates team activities, meetings, and communication",
                input_schema={
                    "type": "object",
                    "properties": {
                        "team_members": {"type": "array", "items": {"type": "string"}},
                        "meeting_type": {"type": "string"},
                        "agenda": {"type": "string"}
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "meeting_id": {"type": "string"},
                        "schedule": {"type": "object"},
                        "participants": {"type": "array"}
                    }
                },
                tools=["schedule_meeting", "send_notification", "update_team_status"]
            ),
            system_prompt=self._get_team_coordinator_prompt()
        )
        
        # Risk Assessor Agent
        self.agents[AgentType.RISK_ASSESSOR] = ProjectManagementAgent(
            agent_type=AgentType.RISK_ASSESSOR,
            capability=AgentCapability(
                name="Risk Assessment",
                description="Identifies and assesses project risks and mitigation strategies",
                input_schema={
                    "type": "object",
                    "properties": {
                        "project_context": {"type": "string"},
                        "risk_factors": {"type": "array", "items": {"type": "string"}}
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "risks": {"type": "array"},
                        "mitigation_strategies": {"type": "array"},
                        "risk_score": {"type": "number"}
                    }
                },
                tools=["assess_risk", "create_mitigation_plan", "update_risk_register"]
            ),
            system_prompt=self._get_risk_assessor_prompt()
        )
        
        # Progress Tracker Agent
        self.agents[AgentType.PROGRESS_TRACKER] = ProjectManagementAgent(
            agent_type=AgentType.PROGRESS_TRACKER,
            capability=AgentCapability(
                name="Progress Tracking",
                description="Tracks project progress and generates reports",
                input_schema={
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string"},
                        "metrics": {"type": "array", "items": {"type": "string"}}
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "progress_report": {"type": "object"},
                        "metrics": {"type": "object"},
                        "recommendations": {"type": "array"}
                    }
                },
                tools=["generate_report", "calculate_metrics", "update_progress"]
            ),
            system_prompt=self._get_progress_tracker_prompt()
        )
    
    def get_agent(self, agent_type: AgentType) -> Optional[ProjectManagementAgent]:
        """Get agent by type"""
        return self.agents.get(agent_type)
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all available agents"""
        return [
            {
                "type": agent_type.value,
                "capability": agent.capability.name,
                "description": agent.capability.description
            }
            for agent_type, agent in self.agents.items()
        ]
    
    async def route_request(
        self,
        user_input: str,
        context: AgentContext
    ) -> Dict[str, Any]:
        """
        Route user request to appropriate agent(s)
        
        Args:
            user_input: User's input message
            context: Agent execution context
            
        Returns:
            Response from appropriate agent(s)
        """
        # Simple routing logic - can be enhanced with ML
        agent_type = self._determine_agent_type(user_input)
        
        if agent_type and agent_type in self.agents:
            agent = self.agents[agent_type]
            return await agent.execute(user_input, context)
        else:
            # Default to project planner for general requests
            agent = self.agents[AgentType.PROJECT_PLANNER]
            return await agent.execute(user_input, context)
    
    def _determine_agent_type(self, user_input: str) -> Optional[AgentType]:
        """Determine which agent should handle the request"""
        user_input_lower = user_input.lower()
        
        # Simple keyword-based routing
        if any(word in user_input_lower for word in ['task', 'assign', 'todo', 'work item']):
            return AgentType.TASK_MANAGER
        elif any(word in user_input_lower for word in ['team', 'meeting', 'coordinate', 'collaborate']):
            return AgentType.TEAM_COORDINATOR
        elif any(word in user_input_lower for word in ['risk', 'issue', 'problem', 'concern']):
            return AgentType.RISK_ASSESSOR
        elif any(word in user_input_lower for word in ['progress', 'status', 'report', 'track']):
            return AgentType.PROGRESS_TRACKER
        elif any(word in user_input_lower for word in ['plan', 'project', 'timeline', 'milestone']):
            return AgentType.PROJECT_PLANNER
        else:
            return None
    
    def _get_project_planner_prompt(self) -> str:
        """Get system prompt for project planner agent"""
        return """You are a Project Planning Agent specialized in creating comprehensive project plans.

Your capabilities:
- Create detailed project plans with timelines and milestones
- Break down complex projects into manageable tasks
- Identify dependencies and critical path
- Suggest resource allocation strategies
- Provide project estimation and planning advice

Always provide structured, actionable project plans that include:
1. Project overview and objectives
2. Detailed task breakdown
3. Timeline with milestones
4. Resource requirements
5. Risk considerations
6. Success metrics

Be thorough, professional, and focus on practical project management best practices."""

    def _get_task_manager_prompt(self) -> str:
        """Get system prompt for task manager agent"""
        return """You are a Task Management Agent specialized in managing individual tasks and assignments.

Your capabilities:
- Create, assign, and track tasks
- Manage task dependencies and priorities
- Set deadlines and reminders
- Monitor task progress and status
- Optimize task workflows

Always provide clear, actionable task management solutions that include:
1. Task details and requirements
2. Assignment and ownership
3. Priority and deadline
4. Dependencies and blockers
5. Progress tracking methods

Be organized, efficient, and focus on task completion and team productivity."""

    def _get_team_coordinator_prompt(self) -> str:
        """Get system prompt for team coordinator agent"""
        return """You are a Team Coordination Agent specialized in managing team activities and communication.

Your capabilities:
- Schedule meetings and coordinate team activities
- Manage team communication and collaboration
- Track team member availability and workload
- Facilitate team decision-making
- Organize team events and activities

Always provide effective team coordination solutions that include:
1. Meeting schedules and agendas
2. Communication plans
3. Team member assignments
4. Collaboration strategies
5. Conflict resolution approaches

Be collaborative, inclusive, and focus on team effectiveness and communication."""

    def _get_risk_assessor_prompt(self) -> str:
        """Get system prompt for risk assessor agent"""
        return """You are a Risk Assessment Agent specialized in identifying and managing project risks.

Your capabilities:
- Identify potential project risks and issues
- Assess risk probability and impact
- Develop mitigation strategies
- Monitor risk indicators
- Provide risk management recommendations

Always provide comprehensive risk assessments that include:
1. Risk identification and categorization
2. Risk probability and impact analysis
3. Mitigation strategies and contingency plans
4. Risk monitoring and reporting
5. Risk management best practices

Be thorough, analytical, and focus on proactive risk management."""

    def _get_progress_tracker_prompt(self) -> str:
        """Get system prompt for progress tracker agent"""
        return """You are a Progress Tracking Agent specialized in monitoring project progress and generating reports.

Your capabilities:
- Track project progress and metrics
- Generate progress reports and dashboards
- Calculate key performance indicators
- Identify progress issues and bottlenecks
- Provide progress improvement recommendations

Always provide detailed progress tracking solutions that include:
1. Progress metrics and KPIs
2. Visual progress reports
3. Trend analysis and forecasting
4. Issue identification and resolution
5. Performance improvement recommendations

Be data-driven, analytical, and focus on measurable project success."""


# Global agent manager instance
agent_manager = ProjectManagementAgentManager()
