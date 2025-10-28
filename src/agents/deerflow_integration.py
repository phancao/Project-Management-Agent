"""
DeerFlow Integration for Project Management Agents
Integrates OpenAI AgentSDK agents with DeerFlow research capabilities
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from src.utils.logger import get_logger
from src.utils.errors import ProjectManagementError
from src.agents.pm_agent_manager import ProjectManagementAgentManager, AgentContext, AgentType
from src.agents.tools import pm_tools
from src.graph.builder import build_graph
from src.graph.types import State


logger = get_logger(__name__)


class DeerFlowProjectManagementIntegration:
    """Integrates DeerFlow research with Project Management Agents"""
    
    def __init__(self):
        self.agent_manager = ProjectManagementAgentManager()
        self.deerflow_graph = None
        self._initialize_deerflow()
    
    def _initialize_deerflow(self):
        """Initialize DeerFlow graph"""
        try:
            self.deerflow_graph = build_graph()
            logger.info("DeerFlow graph initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DeerFlow: {e}")
            raise ProjectManagementError(f"Failed to initialize DeerFlow: {str(e)}")
    
    async def process_request(
        self,
        user_input: str,
        user_id: str,
        project_id: Optional[str] = None,
        session_id: str = None
    ) -> Dict[str, Any]:
        """
        Process user request using integrated DeerFlow + PM Agents
        
        Args:
            user_input: User's input message
            user_id: User ID
            project_id: Optional project ID
            session_id: Optional session ID
            
        Returns:
            Integrated response from DeerFlow and PM agents
        """
        try:
            # Create agent context
            context = AgentContext(
                user_id=user_id,
                project_id=project_id,
                session_id=session_id or f"session_{datetime.now().timestamp()}"
            )
            
            # Determine if we need research (DeerFlow) or project management (PM Agents)
            needs_research = self._needs_research(user_input)
            
            if needs_research:
                # Use DeerFlow for research
                research_result = await self._run_deerflow_research(user_input)
                
                # Then use PM agents to process the research results
                pm_result = await self._process_with_pm_agents(
                    user_input, context, research_result
                )
                
                return {
                    "type": "research_and_planning",
                    "research": research_result,
                    "project_management": pm_result,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                # Use PM agents directly
                pm_result = await self.agent_manager.route_request(user_input, context)
                
                return {
                    "type": "project_management",
                    "project_management": pm_result,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to process request: {e}")
            raise ProjectManagementError(f"Failed to process request: {str(e)}")
    
    def _needs_research(self, user_input: str) -> bool:
        """Determine if the request needs research capabilities"""
        research_keywords = [
            'research', 'find', 'search', 'investigate', 'analyze',
            'market', 'competitor', 'trend', 'best practice', 'how to',
            'what is', 'compare', 'evaluate', 'study', 'learn'
        ]
        
        user_input_lower = user_input.lower()
        return any(keyword in user_input_lower for keyword in research_keywords)
    
    async def _run_deerflow_research(self, user_input: str) -> Dict[str, Any]:
        """Run DeerFlow research on the user input"""
        try:
            # Create DeerFlow state
            state = State(
                messages=[{"role": "user", "content": user_input}],
                current_step="research",
                research_results=[],
                plan=[],
                code="",
                report=""
            )
            
            # Run DeerFlow graph
            result = await self.deerflow_graph.ainvoke(state)
            
            return {
                "success": True,
                "research_results": result.get("research_results", []),
                "plan": result.get("plan", []),
                "report": result.get("report", ""),
                "sources": result.get("sources", [])
            }
            
        except Exception as e:
            logger.error(f"DeerFlow research failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "research_results": [],
                "plan": [],
                "report": "Research failed due to technical issues."
            }
    
    async def _process_with_pm_agents(
        self,
        user_input: str,
        context: AgentContext,
        research_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process research results with project management agents"""
        try:
            # Enhance user input with research context
            enhanced_input = self._enhance_input_with_research(user_input, research_result)
            
            # Route to appropriate PM agent
            pm_result = await self.agent_manager.route_request(enhanced_input, context)
            
            # Add research context to PM result
            pm_result["research_context"] = {
                "has_research": research_result.get("success", False),
                "research_summary": research_result.get("report", "")[:500] + "..." if research_result.get("report") else None,
                "sources_count": len(research_result.get("sources", []))
            }
            
            return pm_result
            
        except Exception as e:
            logger.error(f"PM agent processing failed: {e}")
            return {
                "agent_type": "error",
                "response": f"Failed to process with project management agents: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def _enhance_input_with_research(
        self,
        user_input: str,
        research_result: Dict[str, Any]
    ) -> str:
        """Enhance user input with research findings"""
        if not research_result.get("success"):
            return user_input
        
        research_summary = research_result.get("report", "")
        sources = research_result.get("sources", [])
        
        enhanced_input = f"""
{user_input}

Based on the following research findings, please help with project management:

RESEARCH SUMMARY:
{research_summary}

SOURCES:
{', '.join(sources[:5])}  # Limit to first 5 sources

Please incorporate these research findings into your project management recommendations.
"""
        
        return enhanced_input
    
    async def create_project_with_research(
        self,
        project_description: str,
        user_id: str,
        research_requirements: List[str] = None
    ) -> Dict[str, Any]:
        """
        Create a project with integrated research
        
        Args:
            project_description: Description of the project
            user_id: User ID
            research_requirements: List of research topics to investigate
            
        Returns:
            Project creation result with research integration
        """
        try:
            # Step 1: Research phase
            research_queries = research_requirements or [
                f"best practices for {project_description}",
                f"project management methodologies for {project_description}",
                f"common challenges in {project_description} projects"
            ]
            
            research_results = []
            for query in research_queries:
                research_result = await self._run_deerflow_research(query)
                research_results.append({
                    "query": query,
                    "result": research_result
                })
            
            # Step 2: Project creation with research context
            context = AgentContext(user_id=user_id)
            
            # Create project using PM tools
            project_result = await pm_tools.create_project(
                name=f"Project: {project_description}",
                description=project_description,
                owner=user_id
            )
            
            # Step 3: Generate project plan with research insights
            research_summary = self._summarize_research_results(research_results)
            
            plan_input = f"""
Create a comprehensive project plan for: {project_description}

RESEARCH INSIGHTS:
{research_summary}

Please create a detailed project plan including:
1. Project phases and milestones
2. Task breakdown
3. Resource requirements
4. Risk assessment
5. Timeline estimation
"""
            
            plan_result = await self.agent_manager.route_request(plan_input, context)
            
            return {
                "success": True,
                "project": project_result,
                "research": research_results,
                "project_plan": plan_result,
                "research_summary": research_summary
            }
            
        except Exception as e:
            logger.error(f"Failed to create project with research: {e}")
            raise ProjectManagementError(f"Failed to create project with research: {str(e)}")
    
    def _summarize_research_results(self, research_results: List[Dict[str, Any]]) -> str:
        """Summarize multiple research results"""
        summaries = []
        
        for result in research_results:
            if result["result"].get("success"):
                report = result["result"].get("report", "")
                if report:
                    summaries.append(f"Query: {result['query']}\nSummary: {report[:300]}...")
        
        return "\n\n".join(summaries) if summaries else "No research results available."
    
    async def get_agent_capabilities(self) -> Dict[str, Any]:
        """Get capabilities of all integrated agents"""
        try:
            pm_agents = self.agent_manager.list_agents()
            
            return {
                "project_management_agents": pm_agents,
                "deerflow_capabilities": {
                    "research": "Web search and information gathering",
                    "analysis": "Data analysis and insights",
                    "reporting": "Comprehensive report generation"
                },
                "integration_features": [
                    "Research-enhanced project planning",
                    "Intelligent agent routing",
                    "Context-aware responses",
                    "Multi-agent collaboration"
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get agent capabilities: {e}")
            raise ProjectManagementError(f"Failed to get agent capabilities: {str(e)}")


# Global integration instance
deerflow_pm_integration = DeerFlowProjectManagementIntegration()


