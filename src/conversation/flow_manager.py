"""
Conversation Flow Manager for Project Management Agent

This module handles adaptive conversation flows, intent classification,
and progressive data gathering for project management tasks.
"""

import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

class IntentType(Enum):
    """Types of user intents"""
    CREATE_PROJECT = "create_project"
    PLAN_TASKS = "plan_tasks"
    RESEARCH_TOPIC = "research_topic"
    UPDATE_PROJECT = "update_project"
    GET_STATUS = "get_status"
    HELP = "help"
    # New Project Management intents
    CREATE_WBS = "create_wbs"
    SPRINT_PLANNING = "sprint_planning"
    ASSIGN_TASKS = "assign_tasks"
    CHECK_RESOURCES = "check_resources"
    CREATE_REPORT = "create_report"
    TASK_BREAKDOWN = "task_breakdown"
    DEPENDENCY_ANALYSIS = "dependency_analysis"
    GANTT_CHART = "gantt_chart"
    UNKNOWN = "unknown"

class FlowState(Enum):
    """Conversation flow states"""
    INTENT_DETECTION = "intent_detection"
    CONTEXT_GATHERING = "context_gathering"
    RESEARCH_PHASE = "research_phase"
    PLANNING_PHASE = "planning_phase"
    EXECUTION_PHASE = "execution_phase"
    FEEDBACK_PHASE = "feedback_phase"
    COMPLETED = "completed"

@dataclass
class ConversationContext:
    """Context for ongoing conversation"""
    session_id: str
    current_state: FlowState
    intent: IntentType
    gathered_data: Dict[str, Any]
    required_fields: List[str]
    conversation_history: List[Dict[str, str]]
    created_at: datetime
    updated_at: datetime

@dataclass
class ProjectRequirements:
    """Project requirements gathered from conversation"""
    name: Optional[str] = None
    description: Optional[str] = None
    domain: Optional[str] = None
    timeline: Optional[str] = None
    team_size: Optional[int] = None
    budget: Optional[float] = None
    priority: Optional[str] = None
    technologies: Optional[List[str]] = None
    goals: Optional[List[str]] = None

class ConversationFlowManager:
    """Manages adaptive conversation flows for project management"""
    
    def __init__(self, db_session=None):
        self.contexts: Dict[str, ConversationContext] = {}
        self.intent_classifier = IntentClassifier(use_llm=True)
        self.question_generator = QuestionGenerator()
        self.data_validator = DataValidator()
        self.data_extractor = DataExtractor()
        self.db_session = db_session
        
        # Initialize self-learning system
        self.self_learning = None
        if db_session:
            try:
                from src.conversation.self_learning import SelfLearningSystem
                self.self_learning = SelfLearningSystem(db_session)
                logger.info("Self-learning system initialized")
            except Exception as e:
                logger.warning(f"Could not initialize self-learning: {e}")
        
        # Import DeerFlow workflow for research tasks
        try:
            from src.workflow import run_agent_workflow_async
            self.run_deerflow_workflow = run_agent_workflow_async
        except ImportError:
            logger.warning("DeerFlow workflow not available")
            self.run_deerflow_workflow = None
        
    async def process_message(
        self, 
        message: str, 
        session_id: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process incoming message and return appropriate response
        
        Args:
            message: User's message
            session_id: Unique session identifier
            user_id: Optional user identifier
            
        Returns:
            Response dictionary with message, actions, and metadata
        """
        # Get or create context
        context = self._get_or_create_context(session_id, user_id)
        
        # Update conversation history
        context.conversation_history.append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Classify intent if not already done
        if context.current_state == FlowState.INTENT_DETECTION:
            context.intent = await self.intent_classifier.classify(
                message, 
                conversation_history=context.conversation_history
            )
            
            # Record classification for learning
            if self.self_learning:
                classification_id = self.self_learning.record_classification(
                    session_id=session_id,
                    message=message,
                    classified_intent=context.intent.value,
                    confidence_score=0.8,  # TODO: Get actual confidence from LLM
                    conversation_history=context.conversation_history
                )
                # Store classification ID in context for later feedback
                context.gathered_data['last_classification_id'] = classification_id
            
            context.current_state = FlowState.CONTEXT_GATHERING
            
        # Check if we have enough context
        if context.current_state == FlowState.CONTEXT_GATHERING:
            # Try to extract data from the current message
            extracted_data = await self.data_extractor.extract_project_data(
                message=message,
                intent=context.intent,
                gathered_data=context.gathered_data
            )
            
            # Merge extracted data into gathered_data
            context.gathered_data.update(extracted_data)
            
            if await self._has_enough_context(context):
                context.current_state = FlowState.RESEARCH_PHASE
            else:
                return await self._generate_clarification_response(context)
        
        # Execute appropriate action based on state
        if context.current_state == FlowState.RESEARCH_PHASE:
            # WBS needs research, sprint planning and reports can skip
            skip_research_intents = [IntentType.SPRINT_PLANNING, IntentType.CREATE_REPORT]
            if context.intent in skip_research_intents:
                context.current_state = FlowState.EXECUTION_PHASE
                return await self._handle_execution_phase(context)
            research_result = await self._handle_research_phase(context)
            # If research phase changed state to EXECUTION (e.g., for CREATE_WBS),
            # continue to execution phase instead of returning
            if context.current_state == FlowState.EXECUTION_PHASE:
                # Research completed, now execute
                return await self._handle_execution_phase(context)
            # If research returned None after setting state to something other than EXECUTION, error
            if research_result is None:
                logger.error("Research phase returned None unexpectedly")
                return {
                    "type": "error",
                    "message": "Research phase failed to complete",
                    "state": context.current_state.value
                }
            return research_result
        elif context.current_state == FlowState.PLANNING_PHASE:
            return await self._handle_planning_phase(context)
        elif context.current_state == FlowState.EXECUTION_PHASE:
            return await self._handle_execution_phase(context)
        else:
            return await self._handle_unknown_state(context)
    
    def _get_or_create_context(
        self, 
        session_id: str, 
        user_id: Optional[str] = None
    ) -> ConversationContext:
        """Get existing context or create new one"""
        if session_id not in self.contexts:
            self.contexts[session_id] = ConversationContext(
                session_id=session_id,
                current_state=FlowState.INTENT_DETECTION,
                intent=IntentType.UNKNOWN,
                gathered_data={},
                required_fields=self._get_required_fields_for_intent(IntentType.UNKNOWN),
                conversation_history=[],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        return self.contexts[session_id]
    
    def _get_required_fields_for_intent(self, intent: IntentType) -> List[str]:
        """Get required fields for specific intent"""
        field_mapping = {
            IntentType.CREATE_PROJECT: [
                "name", "description", "domain", "timeline", 
                "team_size", "priority", "goals"
            ],
            IntentType.PLAN_TASKS: [
                "project_id", "task_description", "timeline", "priority"
            ],
            IntentType.RESEARCH_TOPIC: [
                "topic", "depth", "focus_areas"
            ],
            IntentType.UPDATE_PROJECT: [
                "project_id", "update_type", "new_values"
            ],
            IntentType.GET_STATUS: [
                "project_id"
            ],
            IntentType.HELP: [],
            IntentType.UNKNOWN: []
        }
        return field_mapping.get(intent, [])
    
    async def _has_enough_context(self, context: ConversationContext) -> bool:
        """Check if we have enough context to proceed"""
        required_fields = self._get_required_fields_for_intent(context.intent)
        return all(field in context.gathered_data for field in required_fields)
    
    async def _generate_clarification_response(
        self, 
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Generate clarification question to gather more context"""
        missing_fields = self._get_missing_fields(context)
        question = await self.question_generator.generate_question(
            context.intent, 
            missing_fields, 
            context.gathered_data
        )
        
        return {
            "type": "clarification",
            "message": question,
            "missing_fields": missing_fields,
            "state": context.current_state.value,
            "intent": context.intent.value
        }
    
    def _get_missing_fields(self, context: ConversationContext) -> List[str]:
        """Get list of missing required fields"""
        required_fields = self._get_required_fields_for_intent(context.intent)
        return [field for field in required_fields 
                if field not in context.gathered_data]
    
    async def _handle_research_phase(
        self, 
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Handle research phase using DeerFlow"""
        logger.info(f"Starting research phase for intent: {context.intent}")
        
        # For RESEARCH_TOPIC and CREATE_WBS intents, use DeerFlow
        needs_research = context.intent in [IntentType.RESEARCH_TOPIC, IntentType.CREATE_WBS]
        
        if needs_research and self.run_deerflow_workflow:
            # Determine research topic based on intent
            if context.intent == IntentType.CREATE_WBS:
                project_name = context.gathered_data.get("project_name", "")
                project_description = context.gathered_data.get("project_description", "")
                domain = context.gathered_data.get("domain", "")
                topic = f"{project_name} project structure" if project_name else domain if domain else "project structure"
                # Research query for WBS
                user_input = f"Research typical phases, deliverables, and tasks for {domain or project_name or 'this type of project'}. Focus on project structure and common components."
            else:
                topic = context.gathered_data.get("topic", "")
                if not topic:
                    return {
                        "type": "error",
                        "message": "No research topic provided. Please specify what you'd like to research.",
                        "state": context.current_state.value
                    }
                user_input = f"Research: {topic}"
            
            try:
                
                # Call the workflow function (returns final state, not an async iterator)
                result_state = await self.run_deerflow_workflow(
                    user_input=user_input,
                    max_plan_iterations=1,
                    max_step_num=3,
                    enable_background_investigation=True,
                    enable_clarification=False
                )
                
                # Extract research results from final state
                research_result = ""
                if result_state and isinstance(result_state, dict):
                    # Try to get final_report from state
                    research_result = result_state.get("final_report", "")
                    
                    # If no final_report, try to get last message
                    if not research_result and "messages" in result_state:
                        messages = result_state["messages"]
                        if messages:
                            last_message = messages[-1]
                            if hasattr(last_message, 'content'):
                                research_result = last_message.content
                            elif isinstance(last_message, dict):
                                research_result = last_message.get("content", "")
                    
                    # Fallback to observations if available
                    if not research_result:
                        observations = result_state.get("observations", [])
                        if observations:
                            research_result = "\n".join(observations[-3:])  # Last 3 observations
                
                # Store research results in context for execution phase
                if research_result:
                    context.gathered_data['research_context'] = research_result
                    summary_msg = f"Research on '{topic}' completed successfully.\n\n{research_result[:500]}{'...' if len(research_result) > 500 else ''}"
                else:
                    summary_msg = f"Research on '{topic}' has been completed using DeerFlow."
                
                # For CREATE_WBS, move to execution phase after research
                # For RESEARCH_TOPIC, complete here
                if context.intent == IntentType.CREATE_WBS:
                    context.current_state = FlowState.EXECUTION_PHASE
                    # Return None to signal continuation to execution phase
                    # The process_message will continue to handle_execution_phase
                    return None
                else:
                    context.current_state = FlowState.COMPLETED
                    # Return for RESEARCH_TOPIC intent
                    return {
                        "type": "research_completed",
                        "message": summary_msg,
                        "state": context.current_state.value,
                        "data": {
                            "topic": topic,
                            "full_results": research_result if research_result else None
                        }
                    }
            except Exception as e:
                logger.error(f"DeerFlow research failed: {e}")
                return {
                    "type": "error",
                    "message": f"Research failed: {str(e)}",
                    "state": context.current_state.value
                }
        else:
            # For other intents that need research background
            context.current_state = FlowState.PLANNING_PHASE
            
            return {
                "type": "research_started",
                "message": "Starting research phase...",
                "state": context.current_state.value
            }
    
    async def _handle_planning_phase(
        self, 
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Handle planning phase using AgentSDK"""
        # TODO: Integrate with AgentSDK
        context.current_state = FlowState.EXECUTION_PHASE
        
        return {
            "type": "planning_started",
            "message": "Starting planning phase...",
            "state": context.current_state.value
        }
    
    async def _handle_execution_phase(
        self, 
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Handle execution phase"""
        logger.info(f"Executing actions for intent: {context.intent}")
        
        if not self.db_session:
            logger.warning("Database session not available, skipping execution")
            context.current_state = FlowState.COMPLETED
            return {
                "type": "execution_completed",
                "message": "Project management tasks completed (no database available).",
                "state": context.current_state.value
            }
        
        try:
            from database.crud import (
                create_project, create_research_session
            )
            
            # Execute based on intent
            if context.intent == IntentType.CREATE_PROJECT:
                # Create project in database
                project = create_project(
                    db=self.db_session,
                    name=context.gathered_data.get("name", "Untitled Project"),
                    description=context.gathered_data.get("description"),
                    created_by=context.gathered_data.get("created_by"),  # Will need UUID conversion
                    domain=context.gathered_data.get("domain"),
                    priority=context.gathered_data.get("priority", "medium"),
                    timeline_weeks=context.gathered_data.get("timeline_weeks"),
                    budget=context.gathered_data.get("budget")
                )
                
                context.current_state = FlowState.COMPLETED
                return {
                    "type": "execution_completed",
                    "message": f"Project '{project.name}' created successfully!",
                    "state": context.current_state.value,
                    "data": {"project_id": str(project.id)}
                }
            
            elif context.intent == IntentType.RESEARCH_TOPIC:
                # Create research session in database
                session = create_research_session(
                    db=self.db_session,
                    topic=context.gathered_data.get("topic", ""),
                    research_type="general"
                )
                
                context.current_state = FlowState.COMPLETED
                return {
                    "type": "execution_completed",
                    "message": f"Research session '{session.topic}' created successfully!",
                    "state": context.current_state.value,
                    "data": {"research_session_id": str(session.id)}
                }
            
            elif context.intent == IntentType.CREATE_WBS:
                # Use DeerFlow planner for thinking steps
                return await self._handle_create_wbs_with_deerflow_planner(context)
            
            elif context.intent == IntentType.SPRINT_PLANNING:
                # Use DeerFlow planner for thinking steps
                return await self._handle_sprint_planning_with_deerflow_planner(context)
            
            elif context.intent == IntentType.CREATE_REPORT:
                # Generate a report
                return await self._handle_create_report(context)
            
            else:
                context.current_state = FlowState.COMPLETED
                return {
                    "type": "execution_completed",
                    "message": "Actions completed successfully!",
                    "state": context.current_state.value
                }
        
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            return {
                "type": "error",
                "message": f"Execution failed: {str(e)}",
                "state": context.current_state.value
            }
    
    async def _use_deerflow_planner_to_think(
        self,
        user_query: str,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Use LLM to generate a thinking plan for PM tasks using DeerFlow prompt style"""
        try:
            from src.llms.llm import get_llm_by_type
            from src.prompts.template import get_prompt_template
            
            # Load the PM thinking prompt template
            system_prompt = get_prompt_template("pm_thinking", locale="en-US")
            
            # Create messages with system prompt + user query
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ]
            
            llm = get_llm_by_type("basic")
            response = await llm.ainvoke(messages)
            
            content = response.content if hasattr(response, 'content') else str(response)
            logger.info(f"Thinking plan LLM response: {content}")
            
            # Try to extract JSON
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                plan = json.loads(json_match.group())
                logger.info(f"Extracted thinking plan: {plan}")
                return plan
            
            # Fallback
            return {
                "thought": "Planning the requested task",
                "steps": ["Analyzing requirements", "Executing task", "Saving results"]
            }
        except Exception as e:
            logger.warning(f"Could not generate thinking plan: {e}")
            import traceback
            logger.error(f"Full error: {traceback.format_exc()}")
            # Return empty plan on error to not block execution
            return {"thought": "Planning the requested task", "steps": []}
    
    async def _handle_create_wbs_with_deerflow_planner(
        self,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Handle CREATE_WBS using thinking plan"""
        # First, get thinking plan
        user_query = f"Create a Work Breakdown Structure for this project"
        planner_result = await self._use_deerflow_planner_to_think(user_query, context)
        
        # Execute our WBS handler
        result = await self._handle_create_wbs(context)
        
        # If successful, prepend thinking steps
        if result.get("type") == "execution_completed":
            thinking_parts = []
            if planner_result.get("thought"):
                thinking_parts.append(f"💭 {planner_result['thought']}")
            
            if planner_result.get("steps"):
                thinking_parts.append("\n📋 Plan:")
                for i, step in enumerate(planner_result['steps'], 1):
                    # Handle both dict and string step formats
                    if isinstance(step, dict):
                        thinking_parts.append(f"{i}. {step.get('title', str(step))}")
                    else:
                        thinking_parts.append(f"{i}. {step}")
            
            if thinking_parts:
                result["message"] = "🤔 **Thinking:**\n\n" + "\n".join(thinking_parts) + "\n\n✅ " + result["message"]
        
        return result
    
    async def _handle_sprint_planning_with_deerflow_planner(
        self,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Handle SPRINT_PLANNING using thinking plan"""
        # First, get thinking plan
        user_query = f"Plan sprints for this project"
        planner_result = await self._use_deerflow_planner_to_think(user_query, context)
        
        # Execute our sprint handler
        result = await self._handle_sprint_planning(context)
        
        # If successful, prepend thinking steps
        if result.get("type") == "execution_completed":
            thinking_parts = []
            if planner_result.get("thought"):
                thinking_parts.append(f"💭 {planner_result['thought']}")
            
            if planner_result.get("steps"):
                thinking_parts.append("\n📋 Plan:")
                for i, step in enumerate(planner_result['steps'], 1):
                    # Handle both dict and string step formats
                    if isinstance(step, dict):
                        thinking_parts.append(f"{i}. {step.get('title', str(step))}")
                    else:
                        thinking_parts.append(f"{i}. {step}")
            
            if thinking_parts:
                result["message"] = "🤔 **Thinking:**\n\n" + "\n".join(thinking_parts) + "\n\n✅ " + result["message"]
        
        return result
    
    async def _handle_create_wbs(
        self,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Handle CREATE_WBS intent - Generate WBS for a project"""
        logger.info("Handling CREATE_WBS intent")
        
        try:
            from src.handlers import WBSGenerator
            from src.llms.llm import get_llm_by_type
            from database.crud import create_task, get_project
            from uuid import UUID
            
            # Get project information
            project_id = context.gathered_data.get("project_id")
            project_name = context.gathered_data.get("project_name")
            project_description = context.gathered_data.get("project_description")
            breakdown_levels = context.gathered_data.get("breakdown_levels", 3)
            use_research = context.gathered_data.get("use_research", True)
            
            logger.info(f"CREATE_WBS - project_id: {project_id}, project_name: {project_name}")
            logger.info(f"CREATE_WBS - gathered_data: {context.gathered_data}")
            
            # Get project from database if project_id provided
            project = None
            if project_id:
                try:
                    # Try UUID first
                    try:
                        project = get_project(self.db_session, UUID(project_id))
                    except (ValueError, TypeError):
                        # If not a UUID, search by name
                        from database.crud import get_projects
                        all_projects = get_projects(self.db_session)
                        for p in all_projects:
                            if p.name == project_id:
                                project = p
                                break
                    
                    if project:
                        project_name = project.name
                        project_description = project.description
                        project_id = str(project.id)  # Update to actual UUID
                except Exception as e:
                    logger.warning(f"Could not fetch project: {e}")
            
            # If we have project_name but no project object, search by name
            if project_name and not project:
                try:
                    from database.crud import get_projects
                    all_projects = get_projects(self.db_session)
                    for p in all_projects:
                        if p.name == project_name:
                            project = p
                            project_id = str(project.id)
                            project_description = project.description
                            break
                except Exception as e:
                    logger.warning(f"Could not search for project: {e}")
            
            if not project_name:
                return {
                    "type": "error",
                    "message": "Project name is required to create a WBS. Please specify which project.",
                    "state": context.current_state.value
                }
            
            # Initialize WBS generator with LLM
            llm = get_llm_by_type("basic")
            wbs_generator = WBSGenerator(llm=llm)
            
            # Generate WBS without internal research (too slow)
            # WBSGenerator will create tasks based on LLM knowledge
            wbs_result = await wbs_generator.generate_wbs(
                project_name=project_name,
                project_description=project_description or "",
                project_domain=context.gathered_data.get("domain"),
                breakdown_levels=breakdown_levels,
                use_research=False,  # Disabled for speed
                external_research_context=""
            )
            
            # Flatten WBS and create tasks in database if project_id provided
            tasks_created = 0
            logger.info(f"CREATE_WBS - project object: {project}, project.id: {project.id if project else None}")
            if project and project.id:
                try:
                    flat_tasks = wbs_generator.flatten_wbs(wbs_result["wbs_structure"])
                    logger.info(f"CREATE_WBS - flattened {len(flat_tasks)} tasks from WBS")
                    
                    from database.orm_models import Task
                    
                    # Create tasks using ORM directly to avoid commit issues
                    for task_data in flat_tasks:
                        try:
                            task = Task(
                                project_id=project.id,
                                title=task_data.title,
                                description=task_data.description,
                                priority=task_data.priority,
                                estimated_hours=task_data.estimated_hours,
                                status="todo"
                            )
                            self.db_session.add(task)
                            tasks_created += 1
                        except Exception as e:
                            logger.warning(f"Could not add task '{task_data.title}': {e}")
                    
                    # Commit all tasks at once
                    self.db_session.commit()
                    logger.info(f"Created {tasks_created} tasks from WBS")
                except Exception as e:
                    logger.error(f"Could not create tasks in database: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    self.db_session.rollback()
            else:
                logger.warning(f"CREATE_WBS - Skipping task creation: project={project}, project.id={project.id if project else None}")
            
            context.current_state = FlowState.COMPLETED
            return {
                "type": "execution_completed",
                "message": f"WBS generated successfully for '{project_name}'! Created {wbs_result['total_tasks']} tasks.",
                "state": context.current_state.value,
                "data": {
                    "wbs": wbs_result,
                    "tasks_created": tasks_created
                }
            }
        
        except Exception as e:
            logger.error(f"WBS generation failed: {e}")
            return {
                "type": "error",
                "message": f"Failed to generate WBS: {str(e)}",
                "state": context.current_state.value
            }
    
    async def _handle_sprint_planning(
        self,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Handle SPRINT_PLANNING intent - Create a sprint plan"""
        logger.info("Handling SPRINT_PLANNING intent")
        
        try:
            from src.handlers import SprintPlanner
            from database.crud import get_project
            from uuid import UUID
            
            # Get sprint information
            project_id = context.gathered_data.get("project_id")
            sprint_name = context.gathered_data.get("sprint_name", "Sprint 1")
            duration_weeks = context.gathered_data.get("duration_weeks", 2)
            team_capacity = context.gathered_data.get("capacity_hours_per_day", 6.0)
            
            logger.info(f"SPRINT_PLANNING - project_id: {project_id}")
            logger.info(f"SPRINT_PLANNING - gathered_data: {context.gathered_data}")
            
            if not project_id:
                return {
                    "type": "error",
                    "message": "Project ID is required to plan a sprint. Please specify which project.",
                    "state": context.current_state.value
                }
            
            # Verify project exists
            try:
                project = get_project(self.db_session, UUID(project_id))
                if not project:
                    return {
                        "type": "error",
                        "message": f"Project with ID {project_id} not found.",
                        "state": context.current_state.value
                    }
            except Exception as e:
                logger.warning(f"Could not fetch project: {e}")
                return {
                    "type": "error",
                    "message": f"Invalid project ID format: {project_id}",
                    "state": context.current_state.value
                }
            
            # Initialize sprint planner
            planner = SprintPlanner(db_session=self.db_session)
            
            # Generate sprint plan
            sprint_plan = await planner.plan_sprint(
                project_id=project_id,
                sprint_name=sprint_name,
                duration_weeks=duration_weeks,
                team_capacity_hours_per_day=team_capacity
            )
            
            context.current_state = FlowState.COMPLETED
            return {
                "type": "execution_completed",
                "message": f"Sprint '{sprint_name}' planned successfully! Assigned {sprint_plan['tasks_assigned']} tasks.",
                "state": context.current_state.value,
                "data": sprint_plan
            }
        
        except Exception as e:
            logger.error(f"Sprint planning failed: {e}")
            return {
                "type": "error",
                "message": f"Failed to plan sprint: {str(e)}",
                "state": context.current_state.value
            }
    
    async def _handle_create_report(
        self,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Handle CREATE_REPORT intent - Generate a project report"""
        logger.info("Handling CREATE_REPORT intent")
        
        try:
            from src.handlers import ReportGenerator
            
            # Get report parameters
            project_id = context.gathered_data.get("project_id")
            report_type = context.gathered_data.get("report_type", "status")
            include_research = context.gathered_data.get("include_research", True)
            format_type = context.gathered_data.get("format", "markdown")
            
            if not project_id:
                return {
                    "type": "error",
                    "message": "Project ID is required to generate a report. Please specify which project.",
                    "state": context.current_state.value
                }
            
            # Initialize report generator
            generator = ReportGenerator(db_session=self.db_session)
            
            # Generate report
            report = await generator.generate_report(
                project_id=project_id,
                report_type=report_type,
                include_research=include_research,
                format=format_type
            )
            
            if "error" in report:
                return {
                    "type": "error",
                    "message": report["error"],
                    "state": context.current_state.value
                }
            
            context.current_state = FlowState.COMPLETED
            return {
                "type": "execution_completed",
                "message": f"Report generated successfully for '{report.get('project_name', 'project')}'!",
                "state": context.current_state.value,
                "data": {
                    "report_type": report_type,
                    "format": format_type,
                    "content": report.get("content", "")[:1000],  # Preview
                    "sections": report.get("sections", 0)
                }
            }
        
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return {
                "type": "error",
                "message": f"Failed to generate report: {str(e)}",
                "state": context.current_state.value
            }
    
    async def _handle_unknown_state(
        self, 
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Handle unknown state"""
        return {
            "type": "error",
            "message": "I'm not sure how to help with that. Could you please clarify?",
            "state": context.current_state.value
        }
    
    async def record_user_feedback(
        self,
        classification_id: str,
        feedback_type: str,
        was_correct: bool = None,
        user_corrected_intent: str = None,
        user_comment: str = None
    ) -> bool:
        """Record user feedback on classification (called by API endpoint)"""
        if not self.self_learning:
            return False
        
        try:
            self.self_learning.record_feedback(
                classification_id=classification_id,
                feedback_type=feedback_type,
                was_correct=was_correct,
                user_corrected_intent=user_corrected_intent,
                user_comment=user_comment
            )
            return True
        except Exception as e:
            logger.error(f"Failed to record user feedback: {e}")
            return False


class IntentClassifier:
    """Classifies user intent from messages using LLM"""
    
    def __init__(self, use_llm: bool = True):
        """Initialize intent classifier
        
        Args:
            use_llm: If True, use LLM for classification; otherwise use keyword matching
        """
        self.use_llm = use_llm
        
        # Fallback keyword patterns for when LLM is not available
        self.intent_patterns = {
            IntentType.CREATE_PROJECT: [
                "create project", "new project", "start project", 
                "begin project", "project planning"
            ],
            IntentType.PLAN_TASKS: [
                "plan tasks", "task planning", "create tasks", 
                "break down", "task breakdown"
            ],
            IntentType.RESEARCH_TOPIC: [
                "research", "investigate", "find out about", 
                "learn about", "study"
            ],
            IntentType.UPDATE_PROJECT: [
                "update project", "modify project", "change project",
                "edit project"
            ],
            IntentType.GET_STATUS: [
                "status", "progress", "how is", "project status"
            ],
            IntentType.CREATE_WBS: [
                "create wbs", "work breakdown", "work breakdown structure"
            ],
            IntentType.SPRINT_PLANNING: [
                "sprint planning", "plan sprint", "sprint"
            ],
            IntentType.CREATE_REPORT: [
                "create report", "generate report", "make report"
            ],
            IntentType.HELP: [
                "help", "what can you do", "how to", "guide"
            ]
        }
        
        # Try to get LLM for classification
        self.llm = None
        if self.use_llm:
            try:
                from src.llms.llm import get_llm_by_type
                self.llm = get_llm_by_type("basic")
                logger.info("LLM-based intent classifier initialized")
            except Exception as e:
                logger.warning(f"Could not initialize LLM for intent classification: {e}")
                self.llm = None
    
    async def classify(self, message: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> IntentType:
        """Classify user intent from message using LLM or fallback to keywords"""
        
        # Use LLM if available
        if self.llm:
            return await self._classify_with_llm(message, conversation_history)
        else:
            return await self._classify_with_keywords(message)
    
    async def _classify_with_llm(self, message: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> IntentType:
        """Classify intent using LLM"""
        try:
            # Build context with available intents
            intent_descriptions = {
                "create_project": "User wants to create a new project",
                "plan_tasks": "User wants to plan or break down tasks",
                "research_topic": "User wants to research a topic",
                "update_project": "User wants to modify an existing project",
                "get_status": "User wants to check project status or progress",
                "create_wbs": "User wants to create a Work Breakdown Structure (WBS)",
                "sprint_planning": "User wants to plan a sprint or sprint cycle",
                "assign_tasks": "User wants to assign tasks to team members",
                "check_resources": "User wants to check resource availability or capacity",
                "create_report": "User wants to generate a report",
                "task_breakdown": "User wants to break down tasks into subtasks",
                "dependency_analysis": "User wants to analyze task dependencies or critical path",
                "gantt_chart": "User wants to create or view a Gantt chart/timeline",
                "help": "User needs help or wants to know what the system can do",
                "unknown": "Intent cannot be determined"
            }
            
            # Build prompt
            intent_list = "\n".join([f"- {key}: {desc}" for key, desc in intent_descriptions.items()])
            
            prompt = f"""You are an intent classifier for a project management system.
            
Given the user's message, classify their intent. Return ONLY the intent key (lowercase with underscore).

Available intents:
{intent_list}

User message: "{message}"

Context: {conversation_history[-2:] if conversation_history else "No previous context"}

Return only the intent key (e.g., "create_project"):"""
            
            # Call LLM
            if not self.llm:
                raise ValueError("LLM not available")
            response = await self.llm.ainvoke(prompt)
            
            # Extract intent from response
            if isinstance(response, str):
                intent_str = response.strip().lower()
            elif hasattr(response, 'content'):
                intent_str = response.content.strip().lower()
            else:
                intent_str = str(response).strip().lower()
            
            # Try to find matching intent
            for intent in IntentType:
                if intent.value == intent_str:
                    logger.info(f"LLM classified intent: {intent_str}")
                    return intent
            
            # Fallback to keyword matching if LLM didn't return a valid intent
            logger.warning(f"LLM returned unknown intent: {intent_str}, falling back to keywords")
            return await self._classify_with_keywords(message)
            
        except Exception as e:
            logger.error(f"LLM-based intent classification failed: {e}, falling back to keywords")
            return await self._classify_with_keywords(message)
    
    async def _classify_with_keywords(self, message: str) -> IntentType:
        """Fallback: classify using keyword matching"""
        import re
        message_lower = message.lower()
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                # Use regex to match pattern with optional words in between
                regex_pattern = pattern.replace(" ", r"\s+\w*\s*")
                if re.search(regex_pattern, message_lower):
                    logger.info(f"Keyword classified intent: {intent.value}")
                    return intent
        
        return IntentType.UNKNOWN

class QuestionGenerator:
    """Generates adaptive clarification questions"""
    
    def __init__(self):
        self.question_templates = {
            IntentType.CREATE_PROJECT: {
                "name": "What would you like to name this project?",
                "description": "Could you describe what this project is about?",
                "domain": "What domain or industry is this project in?",
                "timeline": "What's the expected timeline for this project?",
                "team_size": "How many team members will be working on this project?",
                "priority": "What's the priority level for this project?",
                "goals": "What are the main goals you want to achieve?"
            }
        }
    
    async def generate_question(
        self, 
        intent: IntentType, 
        missing_fields: List[str], 
        gathered_data: Dict[str, Any]
    ) -> str:
        """Generate appropriate clarification question"""
        if not missing_fields:
            return "Is there anything else you'd like to add?"
        
        if intent in self.question_templates:
            templates = self.question_templates[intent]
            for field in missing_fields:
                if field in templates:
                    return templates[field]
        
        return f"Could you provide more information about {missing_fields[0]}?"

class DataValidator:
    """Validates gathered data"""
    
    async def validate_project_data(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate project creation data"""
        errors = []
        
        if "name" in data and not data["name"].strip():
            errors.append("Project name cannot be empty")
        
        if "timeline" in data:
            # TODO: Add timeline validation
            pass
        
        if "team_size" in data:
            try:
                size = int(data["team_size"])
                if size <= 0:
                    errors.append("Team size must be positive")
            except ValueError:
                errors.append("Team size must be a number")
        
        return len(errors) == 0, errors


class DataExtractor:
    """Extracts structured data from user messages using LLM"""
    
    def __init__(self):
        self.llm = None
        try:
            from src.llms.llm import get_llm_by_type
            self.llm = get_llm_by_type("basic")
            logger.info("LLM-based data extractor initialized")
        except Exception as e:
            logger.warning(f"Could not initialize LLM for data extraction: {e}")
            self.llm = None
    
    async def extract_project_data(self, message: str, intent: IntentType, 
                                   gathered_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Extract project-related data from user message using LLM"""
        
        if not self.llm:
            return {}
        
        gathered_data = gathered_data or {}
        
        try:
            # Build extraction prompt based on intent
            field_descriptions = self._get_field_descriptions(intent)
            
            prompt = f"""Extract structured data from the user's message.

Intent: {intent.value}

Available fields to extract:
{field_descriptions}

Already gathered data:
{gathered_data}

User message: "{message}"

Return a JSON object with only the fields that can be extracted from the message.
Return null for fields that are not mentioned or cannot be determined.

Example format: {{"name": "My Project", "budget": 50000, "team_size": 5}}

Return only valid JSON:"""

            response = await self.llm.ainvoke(prompt)
            
            # Extract JSON from response
            if isinstance(response, str):
                response_text = response.strip()
            else:
                response_text = response.content.strip()
            
            # Parse JSON
            import json as json_module
            import re
            
            # Try to find JSON in the response (in case LLM adds extra text)
            json_match = re.search(r'\{[^}]*\}', response_text)
            if json_match:
                extracted_data = json_module.loads(json_match.group())
                logger.info(f"Extracted data: {extracted_data}")
                return extracted_data
            else:
                logger.warning(f"Could not find JSON in LLM response: {response_text}")
                return {}
                
        except Exception as e:
            logger.error(f"Data extraction failed: {e}")
            return {}
    
    def _get_field_descriptions(self, intent: IntentType) -> str:
        """Get field descriptions for data extraction"""
        descriptions = {
            IntentType.CREATE_PROJECT: """- name: Project name
- description: Project description or what it's about
- domain: Industry or domain (e.g., "mobile", "web", "healthcare")
- timeline: Project duration (e.g., "3 months", "12 weeks")
- team_size: Number of team members (integer)
- budget: Budget amount (number, can include currency like "$50000" or "50000")
- priority: Priority level ("low", "medium", "high", "urgent")
- goals: List of project goals or objectives""",
            
            IntentType.UPDATE_PROJECT: """- name: New project name
- description: Updated description
- status: New status
- priority: Updated priority
- timeline_weeks: Updated timeline in weeks""",
            
            IntentType.CREATE_WBS: """- project_name: Name of the project
- project_id: UUID of the project (preferred if available)
- project_description: Description of the project
- domain: Project domain or industry
- breakdown_levels: Number of levels in WBS (default: 3)
- tasks: List of main tasks""",
            
            IntentType.SPRINT_PLANNING: """- project_id: ID of the project
- sprint_duration: Sprint length in weeks
- sprint_goals: List of sprint objectives""",
            
            IntentType.ASSIGN_TASKS: """- task_ids: List of task IDs
- assignee_name: Name of person to assign to
- due_date: Task due date""",
            
            IntentType.CREATE_REPORT: """- report_type: Type of report (e.g., "progress", "status", "summary")
- project_id: ID of the project
- format: Report format (e.g., "pdf", "markdown")""",
            
            IntentType.RESEARCH_TOPIC: """- topic: Research topic
- depth: Research depth level
- focus_areas: Areas to focus on"""
        }
        
        return descriptions.get(intent, "- No specific fields defined")
