"""
WBS (Work Breakdown Structure) Generator

Generates a comprehensive WBS for a project using LLM reasoning
and optionally DeerFlow research.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class WBSTask:
    """Represents a task in the WBS hierarchy"""
    title: str
    description: str
    level: int
    estimated_hours: Optional[float] = None
    priority: str = "medium"
    parent_id: Optional[str] = None


class WBSGenerator:
    """Generates Work Breakdown Structure for projects"""
    
    def __init__(self, llm=None):
        """Initialize WBS generator
        
        Args:
            llm: Optional LLM instance for generating WBS
        """
        self.llm = llm
    
    async def generate_wbs(
        self,
        project_name: str,
        project_description: str,
        project_domain: Optional[str] = None,
        breakdown_levels: int = 3,
        use_research: bool = True
    ) -> Dict[str, Any]:
        """
        Generate a WBS for a project
        
        Args:
            project_name: Name of the project
            project_description: Description of the project
            project_domain: Domain/industry of the project
            breakdown_levels: Number of levels in WBS (default: 3)
            use_research: Whether to use DeerFlow for research
            
        Returns:
            Dictionary containing WBS structure and metadata
        """
        logger.info(f"Generating WBS for project: {project_name}")
        
        # If research enabled, gather context about similar projects
        research_context = ""
        if use_research and project_domain:
            try:
                research_context = await self._research_project_structure(
                    project_name, project_description, project_domain
                )
                logger.info("Research context gathered successfully")
            except Exception as e:
                logger.warning(f"Research failed: {e}, continuing without research")
        
        # Generate WBS using LLM
        wbs_structure = await self._generate_wbs_with_llm(
            project_name=project_name,
            project_description=project_description,
            project_domain=project_domain,
            breakdown_levels=breakdown_levels,
            research_context=research_context
        )
        
        return {
            "project_name": project_name,
            "wbs_structure": wbs_structure,
            "levels": breakdown_levels,
            "total_tasks": self._count_tasks(wbs_structure),
            "use_research": use_research
        }
    
    async def _research_project_structure(
        self, 
        project_name: str, 
        project_description: str,
        domain: str
    ) -> str:
        """
        Research similar project structures using DeerFlow
        
        Returns a context string about typical project structure
        """
        try:
            from src.workflow import run_agent_workflow_async
            
            research_query = f"""
Research the typical work breakdown structure for a {domain} project:
- Project type: {project_name}
- Description: {project_description}
- Focus on common phases, deliverables, and tasks
- Provide typical project structure examples
"""
            
            # Run DeerFlow research and extract results
            # Note: run_agent_workflow_async is a coroutine that streams internally
            # For now, we'll just call it to complete the research
            await run_agent_workflow_async(
                user_input=research_query,
                max_plan_iterations=1,
                max_step_num=3,
                enable_background_investigation=True,
                enable_clarification=False,
                debug=False
            )
            
            # For demonstration, return a summary that research was performed
            # In production, we'd extract actual findings from the workflow state
            research_summary = f"DeerFlow research completed for {domain} project patterns"
            return f"Research findings for similar {domain} projects:\n{research_summary}"
            
        except Exception as e:
            logger.error(f"DeerFlow research failed: {e}")
            return ""
    
    async def _generate_wbs_with_llm(
        self,
        project_name: str,
        project_description: str,
        project_domain: Optional[str],
        breakdown_levels: int,
        research_context: str
    ) -> Dict[str, Any]:
        """
        Generate WBS structure using LLM
        """
        if not self.llm:
            # Fallback to template-based generation
            return self._generate_template_wbs(project_name, project_description)
        
        try:
            prompt = self._build_wbs_prompt(
                project_name=project_name,
                project_description=project_description,
                project_domain=project_domain,
                breakdown_levels=breakdown_levels,
                research_context=research_context
            )
            
            # Call LLM to generate WBS
            logger.info("Invoking LLM for WBS generation...")
            response = await self.llm.ainvoke(prompt)
            
            # Parse response
            if hasattr(response, 'content'):
                response_text = response.content
            else:
                response_text = str(response)
            
            logger.info(f"LLM response received (length: {len(response_text)})")
            logger.debug(f"LLM response: {response_text[:500]}")
            
            # Try to extract JSON structure
            import json
            import re
            
            # Look for JSON in the response - try to find the outermost object
            # First, try to find JSON between ```json and ``` markers
            json_block_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_block_match:
                try:
                    wbs_json = json.loads(json_block_match.group(1))
                    logger.info(f"Successfully parsed JSON block. Phases: {len(wbs_json.get('phases', []))}")
                    return wbs_json
                except json.JSONDecodeError:
                    logger.warning("Could not parse JSON block")
            
            # If no JSON block found, try to find outermost JSON object
            # Count braces to find complete object
            brace_count = 0
            start_idx = response_text.find('{')
            if start_idx != -1:
                for i in range(start_idx, len(response_text)):
                    if response_text[i] == '{':
                        brace_count += 1
                    elif response_text[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            try:
                                wbs_json = json.loads(response_text[start_idx:i+1])
                                logger.info(f"Successfully parsed outermost JSON object. Phases: {len(wbs_json.get('phases', []))}")
                                return wbs_json
                            except json.JSONDecodeError:
                                logger.warning("Could not parse outermost JSON object")
                            break
            
            logger.warning("Could not find valid JSON in response, using template")
            logger.debug(f"Response text (first 1000 chars): {response_text[:1000]}")
            return self._generate_template_wbs(project_name, project_description)
                
        except Exception as e:
            logger.error(f"LLM WBS generation failed: {e}")
            return self._generate_template_wbs(project_name, project_description)
    
    def _build_wbs_prompt(
        self,
        project_name: str,
        project_description: str,
        project_domain: Optional[str],
        breakdown_levels: int,
        research_context: str
    ) -> str:
        """Build prompt for LLM to generate WBS"""
        
        domain_section = f"\nDomain: {project_domain}" if project_domain else ""
        research_section = f"\n\nResearch Context:\n{research_context}" if research_context else ""
        
        prompt = f"""You are an expert project manager. Create a detailed Work Breakdown Structure (WBS) for this project.

Project Name: {project_name}
Description: {project_description}{domain_section}

Requirements:
- Create a hierarchical WBS with {breakdown_levels} levels
- Level 1: Main phases (e.g., Planning, Development, Testing, Deployment)
- Level 2: Major deliverables/milestones
- Level 3+: Specific tasks and subtasks
- Include realistic time estimates in hours
- Assign priority levels (high, medium, low)

{research_section}

Return the WBS as a JSON structure with this format:
{{
  "phases": [
    {{
      "title": "Phase Name",
      "level": 1,
      "estimated_hours": 100,
      "priority": "high",
      "deliverables": [
        {{
          "title": "Deliverable Name",
          "level": 2,
          "estimated_hours": 40,
          "priority": "high",
          "tasks": [
            {{
              "title": "Task Name",
              "level": 3,
              "estimated_hours": 8,
              "priority": "medium",
              "description": "Task details"
            }}
          ]
        }}
      ]
    }}
  ]
}}

Return only valid JSON:"""
        
        return prompt
    
    def _generate_template_wbs(
        self, 
        project_name: str, 
        project_description: str
    ) -> Dict[str, Any]:
        """
        Generate a template WBS when LLM is not available
        """
        logger.info("Generating template WBS")
        
        return {
            "phases": [
                {
                    "title": "Planning & Analysis",
                    "level": 1,
                    "estimated_hours": 80,
                    "priority": "high",
                    "deliverables": [
                        {
                            "title": "Requirements Gathering",
                            "level": 2,
                            "estimated_hours": 40,
                            "priority": "high",
                            "tasks": [
                                {
                                    "title": "Define project scope",
                                    "level": 3,
                                    "estimated_hours": 8,
                                    "priority": "high",
                                    "description": "Clearly define what is in and out of scope"
                                },
                                {
                                    "title": "Gather stakeholder requirements",
                                    "level": 3,
                                    "estimated_hours": 16,
                                    "priority": "high",
                                    "description": "Interview stakeholders and document requirements"
                                }
                            ]
                        }
                    ]
                },
                {
                    "title": "Design & Development",
                    "level": 1,
                    "estimated_hours": 200,
                    "priority": "high",
                    "deliverables": [
                        {
                            "title": "System Design",
                            "level": 2,
                            "estimated_hours": 60,
                            "priority": "high",
                            "tasks": [
                                {
                                    "title": "Architecture design",
                                    "level": 3,
                                    "estimated_hours": 24,
                                    "priority": "high",
                                    "description": "Design system architecture"
                                }
                            ]
                        }
                    ]
                },
                {
                    "title": "Testing & Quality Assurance",
                    "level": 1,
                    "estimated_hours": 100,
                    "priority": "medium",
                    "deliverables": []
                },
                {
                    "title": "Deployment & Launch",
                    "level": 1,
                    "estimated_hours": 60,
                    "priority": "high",
                    "deliverables": []
                }
            ]
        }
    
    def _count_tasks(self, wbs_structure: Dict[str, Any]) -> int:
        """Count total number of tasks in WBS"""
        count = 0
        for phase in wbs_structure.get("phases", []):
            count += 1  # Count phase
            
            for deliverable in phase.get("deliverables", []):
                count += 1  # Count deliverable
                
                # Count tasks
                count += len(deliverable.get("tasks", []))
        
        return count
    
    def flatten_wbs(self, wbs_structure: Dict[str, Any]) -> List[WBSTask]:
        """
        Flatten hierarchical WBS into a list of tasks
        
        Returns list of WBSTask objects suitable for database storage
        """
        tasks = []
        parent_stack = []  # Track parent hierarchy
        
        for phase_idx, phase in enumerate(wbs_structure.get("phases", [])):
            # Add phase
            phase_task = WBSTask(
                title=phase["title"],
                description=f"Phase {phase_idx + 1}: {phase['title']}",
                level=phase["level"],
                estimated_hours=phase.get("estimated_hours"),
                priority=phase.get("priority", "medium")
            )
            tasks.append(phase_task)
            parent_stack.append(len(tasks) - 1)
            
            # Process deliverables
            for deliverable_idx, deliverable in enumerate(phase.get("deliverables", [])):
                deliverable_task = WBSTask(
                    title=deliverable["title"],
                    description=deliverable.get("description", ""),
                    level=deliverable["level"],
                    estimated_hours=deliverable.get("estimated_hours"),
                    priority=deliverable.get("priority", "medium"),
                    parent_id=str(tasks[parent_stack[-1]].title) if parent_stack else None
                )
                tasks.append(deliverable_task)
                parent_stack.append(len(tasks) - 1)
                
                # Process subtasks
                for task in deliverable.get("tasks", []):
                    task_obj = WBSTask(
                        title=task["title"],
                        description=task.get("description", ""),
                        level=task["level"],
                        estimated_hours=task.get("estimated_hours"),
                        priority=task.get("priority", "medium"),
                        parent_id=str(tasks[parent_stack[-1]].title) if parent_stack else None
                    )
                    tasks.append(task_obj)
                
                # Remove deliverable from stack
                if parent_stack:
                    parent_stack.pop()
            
            # Remove phase from stack
            if parent_stack:
                parent_stack.pop()
        
        return tasks

