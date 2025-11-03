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
    UPDATE_TASK = "update_task"
    UPDATE_SPRINT = "update_sprint"
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
    LIST_PROJECTS = "list_projects"
    LIST_TASKS = "list_tasks"
    LIST_SPRINTS = "list_sprints"
    LIST_MY_TASKS = "list_my_tasks"
    GET_PROJECT_STATUS = "get_project_status"
    SWITCH_PROJECT = "switch_project"
    SWITCH_SPRINT = "switch_sprint"
    SWITCH_TASK = "switch_task"
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
        
        # Initialize PM provider (OpenProject, JIRA, etc.)
        self.pm_provider = None
        try:
            from src.pm_providers import build_pm_provider
            self.pm_provider = build_pm_provider(db_session=db_session)
            if self.pm_provider:
                logger.info(f"PM Provider initialized: {self.pm_provider.__class__.__name__}")
        except Exception as e:
            logger.warning(f"Could not initialize PM provider: {e}")
        
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
            from src.workflow import run_agent_workflow_async, run_agent_workflow_stream
            self.run_deerflow_workflow = run_agent_workflow_async
            self.run_deerflow_workflow_stream = run_agent_workflow_stream
        except ImportError:
            logger.warning("DeerFlow workflow not available")
            self.run_deerflow_workflow = None
            self.run_deerflow_workflow_stream = None
        
    async def process_message(
        self, 
        message: str, 
        session_id: str,
        user_id: Optional[str] = None,
        stream_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Process incoming message and return appropriate response
        
        Args:
            message: User's message
            session_id: Unique session identifier
            user_id: Optional user identifier
            stream_callback: Optional callback to yield intermediate results (async function)
            
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
        
        # Reset state for new messages unless explicitly set to INTENT_DETECTION
        # This allows follow-up messages to be processed properly
        if context.current_state == FlowState.COMPLETED:
            context.current_state = FlowState.INTENT_DETECTION
            logger.info(f"Reset state to INTENT_DETECTION for new message (previous state was COMPLETED)")
        
        # Generate PM plan or use existing plan
        if context.current_state == FlowState.INTENT_DETECTION:
            # Extract basic info from message first (project name, etc.)
            initial_data = await self.data_extractor.extract_project_data(
                message=message,
                intent=IntentType.CREATE_WBS,  # Use WBS as default for extraction
                gathered_data=context.gathered_data.copy()  # Pass existing context
            )
            context.gathered_data.update(initial_data)
            logger.info(f"Extracted initial data: {initial_data}")
            
            # Try to generate a PM plan for multi-task execution
            pm_plan = await self.generate_pm_plan(message, context)
            
            if pm_plan and pm_plan.get('steps'):
                # Multi-task execution: use plan-based approach
                context.gathered_data['_pm_plan'] = pm_plan
                context.gathered_data['_current_step_index'] = 0
                context.current_state = FlowState.PLANNING_PHASE
                logger.info(f"Generated PM plan with {len(pm_plan.get('steps', []))} steps")
            else:
                # Fallback to legacy intent-based approach
                logger.info("Could not generate PM plan, falling back to intent-based classification")
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
                        confidence_score=0.8,
                        conversation_history=context.conversation_history
                    )
                    context.gathered_data['last_classification_id'] = classification_id
                
                # Only set to CONTEXT_GATHERING if not already in PLANMNING_PHASE
                if context.current_state != FlowState.PLANNING_PHASE:
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
                # Determine next state based on intent - some need research, others go straight to execution
                needs_research = context.intent in [IntentType.RESEARCH_TOPIC, IntentType.CREATE_WBS]
                logger.info(f"Has enough context. Intent: {context.intent}, needs_research: {needs_research}")
                if needs_research:
                    context.current_state = FlowState.RESEARCH_PHASE
                else:
                    context.current_state = FlowState.EXECUTION_PHASE
                logger.info(f"State set to: {context.current_state}")
            else:
                return await self._generate_clarification_response(context)
        
        logger.info(f"Final current_state: {context.current_state}, intent: {context.intent}")
        
        # Execute appropriate action based on state
        if context.current_state == FlowState.RESEARCH_PHASE:
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
            return await self._handle_planning_phase(context, stream_callback)
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
    
    def _should_use_pm_provider(self) -> bool:
        """Check if PM provider should be used - always True since we removed internal DB"""
        return self.pm_provider is not None
    
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
            IntentType.UPDATE_TASK: [
                # Can work with task_id OR task_title
            ],
            IntentType.UPDATE_SPRINT: [
                # Can work with sprint_id OR sprint_name
            ],
            IntentType.GET_STATUS: [
                "project_id"
            ],
            IntentType.CREATE_WBS: [
                # WBS can work with just project_name OR project_id
            ],
            IntentType.SPRINT_PLANNING: [
                "project_id"
            ],
            IntentType.CREATE_REPORT: [
                "project_id"
            ],
            IntentType.LIST_TASKS: [
                "project_id"
            ],
            IntentType.LIST_MY_TASKS: [
                # No required fields, uses user_id from session context
            ],
            IntentType.LIST_SPRINTS: [
                "project_id"
            ],
            IntentType.GET_PROJECT_STATUS: [
                "project_id"
            ],
            IntentType.LIST_PROJECTS: [
                # No required fields, just lists all projects
            ],
            IntentType.SWITCH_PROJECT: [
                # Can work with project_id OR project_name
            ],
            IntentType.SWITCH_SPRINT: [
                # Can work with sprint_id OR sprint_name (requires project context)
            ],
            IntentType.SWITCH_TASK: [
                # Can work with task_id OR task_title (requires project context)
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
        
        # Skip if research already done (from streaming)
        if context.gathered_data.get('research_already_done'):
            logger.info("Research already completed via streaming, skipping")
            context.current_state = FlowState.EXECUTION_PHASE
            return None
        
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
    
    async def _handle_planning_phase(
        self, 
        context: ConversationContext,
        stream_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Handle plan-based execution phase with optional streaming"""
        import time
        
        start_time = time.time()
        logger.info(f"[TIMING] _handle_planning_phase started")
        
        pm_plan = context.gathered_data.get('_pm_plan')
        if not pm_plan:
            logger.error("Planning phase activated but no PM plan found")
            context.current_state = FlowState.COMPLETED
            return {
                "type": "error",
                "message": "Execution plan not found",
                "state": context.current_state.value
            }
        
        steps = pm_plan.get('steps', [])
        current_step_index = context.gathered_data.get('_current_step_index', 0)
        overall_thought = pm_plan.get('overall_thought', '')
        logger.info(f"[TIMING] Plan has {len(steps)} steps - {time.time() - start_time:.2f}s")
        
        # Build initial response message parts
        response_parts = []
        if overall_thought:
            response_parts.append(f"🤔 **Thinking:**\n\n💭 {overall_thought}\n\n📋 **Plan:**")
            for i, step in enumerate(steps, 1):
                response_parts.append(f"{i}. {step.get('title')}")
            response_parts.append("")
        
        response_parts.append("🚀 **Executing plan...**\n")
        
        # If streaming, yield initial thinking/plan
        if stream_callback:
            await stream_callback("\n".join(response_parts))
        
        # Execute all steps sequentially and build results incrementally
        results = []
        for idx, step in enumerate(steps):
            step_start = time.time()
            logger.info(f"[TIMING] Executing step {idx + 1}/{len(steps)}: {step.get('title')} - {time.time() - start_time:.2f}s")
            
            # Map PMStepType to IntentType and execute
            step_type_str = step.get('step_type')
            step_result = await self._execute_pm_step(step, context)
            
            step_duration = time.time() - step_start
            logger.info(f"[TIMING] Step {idx + 1} completed in {step_duration:.2f}s - {time.time() - start_time:.2f}s total")
            
            results.append({
                'step': step.get('title'),
                'type': step.get('step_type'),
                'result': step_result
            })
            
            # Build this step's result message - extract just the result part
            result_msg = step_result.get('message', 'Completed' if step_result.get('type') == 'execution_completed' else 'Failed')
            
            # Remove thinking/plan sections from message if present (they're in overall plan)
            if "🤔 **Thinking:**" in result_msg:
                # Extract only the part after the last ✅ marker
                parts = result_msg.split("✅ ")
                if len(parts) > 1:
                    # Last part is the actual result
                    result_msg = parts[-1]
                    # Remove leading whitespace
                    result_msg = result_msg.lstrip()
            
            if step_result.get('type') == 'execution_completed':
                step_msg = f"✅ {step.get('title')}\n   {result_msg}"
            else:
                step_msg = f"❌ {step.get('title')}\n   {result_msg}"
            
            response_parts.append(step_msg)
            
            # If streaming, yield this step's result immediately
            if stream_callback:
                await stream_callback(step_msg)
        
        # Don't override state if a switch handler has set it back to INTENT_DETECTION
        if context.current_state != FlowState.INTENT_DETECTION:
            context.current_state = FlowState.COMPLETED
        
        # Build final message from all steps
        final_message = "\n".join(response_parts)
        
        # Individual step messages were already sent during execution via stream_callback
        # The server will handle sending the finish_reason when process_message completes
        
        logger.info(f"[TIMING] Planning phase completed: {len(steps)} steps executed in {time.time() - start_time:.2f}s")
        
        return {
            "type": "execution_completed",
            "message": final_message,
            "state": context.current_state.value
        }
    
    async def _execute_pm_step(
        self,
        step: Dict[str, Any],
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Execute a single PM plan step"""
        from src.prompts.pm_planner_model import PMStepType
        
        step_type = step.get('step_type')
        logger.info(f"Executing PM step: {step_type}")
        
        # Handle both string and enum types
        step_type_str = step_type.value if isinstance(step_type, PMStepType) else step_type
        
        # Map PMStepType to IntentType and execute
        if step_type_str == "create_wbs":
            # Project name already extracted from user message, just execute
            context.intent = IntentType.CREATE_WBS
            return await self._handle_create_wbs_with_deerflow_planner(context)
        
        elif step_type_str == "sprint_planning":
            context.intent = IntentType.SPRINT_PLANNING
            return await self._handle_sprint_planning_with_deerflow_planner(context)
        
        elif step_type_str == "create_project":
            # Extract project info
            context.intent = IntentType.CREATE_PROJECT
            return await self._execute_intent(IntentType.CREATE_PROJECT, context)
        
        elif step_type_str == "research":
            # Intelligent research routing based on step description
            description = step.get('description', '').lower()
            title = step.get('title', '').lower()
            
            # Determine research type from keywords
            # Support both English and Vietnamese keywords for ETA
            eta_keywords = ['eta', 'estimated time', 'time estimation', 'time estimate', 'ước tính thời gian', 'ước tính', 'estimate']
            if any(keyword in description.lower() for keyword in eta_keywords) or any(keyword in title.lower() for keyword in eta_keywords):
                # ETA research: analyze tasks and provide estimates
                return await self._handle_eta_research(context)
            elif 'wbs' in description or 'work breakdown' in description or 'project structure' in description:
                # WBS research: handled by CREATE_WBS via DeerFlow
                logger.warning(f"Research step for WBS should be handled by CREATE_WBS step instead")
                return await self._handle_create_wbs_with_deerflow_planner(context)
            elif 'dependency' in description or 'phụ thuộc' in description:
                # Dependency analysis research
                return await self._handle_dependency_research(context)
            elif 'sprint' in description or 'iter' in description:
                # Sprint planning research
                logger.warning(f"Research step for sprint planning should be handled by SPRINT_PLANNING step instead")
                return await self._handle_sprint_planning_with_deerflow_planner(context)
            else:
                # Generic research using LLM
                return await self._handle_generic_research(context, step)
        
        elif step_type_str == "switch_project":
            return await self._handle_switch_project(context)
        
        elif step_type_str == "switch_sprint":
            return await self._handle_switch_sprint(context)
        
        elif step_type_str == "switch_task":
            return await self._handle_switch_task(context)
        
        elif step_type_str == "list_projects":
            return await self._handle_list_projects(context)
        
        elif step_type_str == "list_tasks":
            return await self._handle_list_tasks(context)
        
        elif step_type_str == "list_my_tasks":
            # Extract date/week filters from user message
            if context.conversation_history:
                last_message = context.conversation_history[-1].get("content", "")
                if last_message:
                    filter_data = await self.data_extractor.extract_project_data(
                        message=last_message,
                        intent=IntentType.LIST_MY_TASKS,
                        gathered_data=context.gathered_data
                    )
                    context.gathered_data.update(filter_data)
                    logger.info(f"Extracted list_my_tasks data: {filter_data}")
            return await self._handle_list_my_tasks(context)
        
        elif step_type_str == "list_sprints":
            return await self._handle_list_sprints(context)
        
        elif step_type_str == "get_project_status":
            return await self._handle_get_project_status(context)
        
        elif step_type_str == "update_task":
            # Extract update data from the last user message before execution
            if context.conversation_history:
                last_message = context.conversation_history[-1].get("content", "")
                if last_message:
                    update_data = await self.data_extractor.extract_project_data(
                        message=last_message,
                        intent=IntentType.UPDATE_TASK,
                        gathered_data=context.gathered_data
                    )
                    context.gathered_data.update(update_data)
                    logger.info(f"Extracted update_task data: {update_data}")
            return await self._handle_update_task(context)
        
        elif step_type_str == "update_sprint":
            # Extract update data from the last user message before execution
            if context.conversation_history:
                last_message = context.conversation_history[-1].get("content", "")
                if last_message:
                    update_data = await self.data_extractor.extract_project_data(
                        message=last_message,
                        intent=IntentType.UPDATE_SPRINT,
                        gathered_data=context.gathered_data
                    )
                    context.gathered_data.update(update_data)
                    logger.info(f"Extracted update_sprint data: {update_data}")
            return await self._handle_update_sprint(context)
        
        elif step_type_str == "create_report":
            context.intent = IntentType.CREATE_REPORT
            return await self._handle_create_report(context)
        
        elif step_type_str == "task_assignment":
            # Extract assignment data from the last user message before execution
            if context.conversation_history:
                last_message = context.conversation_history[-1].get("content", "")
                if last_message:
                    assignment_data = await self.data_extractor.extract_project_data(
                        message=last_message,
                        intent=IntentType.ASSIGN_TASKS,
                        gathered_data=context.gathered_data
                    )
                    context.gathered_data.update(assignment_data)
                    logger.info(f"Extracted task_assignment data: {assignment_data}")
            return await self._handle_task_assignment(context)
        
        elif step_type_str == "gantt_chart":
            context.intent = IntentType.GET_STATUS  # Reuse status for now
            return await self._handle_gantt_chart(context)
        
        elif step_type_str == "dependency_analysis":
            context.intent = IntentType.DEPENDENCY_ANALYSIS
            return await self._handle_dependency_research(context)
        
        elif step_type_str == "unknown":
            logger.warning(f"Unsupported request: {step.get('title', step_type_str)}")
            description = step.get('description', 'This feature is not currently supported.')
            return {
                "type": "execution_completed",
                "message": f"❌ **Feature Not Supported**\n\n{description}\n\n_Please use supported commands like listing tasks, creating WBS, planning sprints, etc._",
                "state": "complete"
            }
        else:
            logger.warning(f"Unknown or unsupported PM step type: {step_type_str}")
            return {
                "type": "error",
                "message": f"❌ **Unsupported Request**\n\nI don't know how to handle '{step.get('title', step_type_str)}'. Please try a supported command like:\n- List my tasks\n- Create WBS\n- Plan sprints\n- Get project status",
                "state": "error"
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
        
        # Use general intent executor
        return await self._execute_intent(context.intent, context)
    
    async def _execute_intent(
        self,
        intent: IntentType,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Execute a specific intent - extracted for reuse in multi-step flows"""
        try:
            from database.crud import (
                create_project, create_research_session
            )
            
            # Execute based on intent
            if intent == IntentType.CREATE_PROJECT:
                # Create project in database
                project = create_project(
                    db=self.db_session,
                    name=context.gathered_data.get("name", "Untitled Project"),
                    description=context.gathered_data.get("description"),
                    created_by=context.gathered_data.get("created_by"),
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
            
            elif intent == IntentType.RESEARCH_TOPIC:
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
            
            elif intent == IntentType.CREATE_WBS:
                # Use DeerFlow planner for thinking steps
                return await self._handle_create_wbs_with_deerflow_planner(context)
            
            elif intent == IntentType.SPRINT_PLANNING:
                # Use DeerFlow planner for thinking steps
                return await self._handle_sprint_planning_with_deerflow_planner(context)
            
            elif intent == IntentType.CREATE_REPORT:
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
            logger.error(f"Execution failed for {intent.value}: {e}")
            return {
                "type": "error",
                "message": f"Execution failed: {str(e)}",
                "state": context.current_state.value
            }
    
    async def generate_pm_plan(
        self,
        user_message: str,
        context: ConversationContext
    ) -> Optional[Dict[str, Any]]:
        """Generate a PM execution plan from user message with conversation history"""
        import time
        plan_start = time.time()
        logger.info("[TIMING] generate_pm_plan started")
        
        try:
            from src.llms.llm import get_llm_by_type
            from src.prompts.template import get_prompt_template
            from src.prompts.pm_planner_model import PMPlan, PMStepType
            
            # Load the PM planner prompt template
            system_prompt = get_prompt_template("pm_planner", locale="en-US")
            
            # Create messages with system prompt + conversation history + current message
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Add key facts summary if available (from gathered_data)
            key_facts = self._extract_key_facts(context)
            if key_facts:
                messages.append({
                    "role": "system",
                    "content": f"**Key Context:**\n{key_facts}\n\nUse this context when planning steps."
                })
                logger.info(f"Added key facts to context: {key_facts[:100]}...")
            
            # Add conversation history if available (optimized context selection)
            if context.conversation_history:
                # Use semantic importance scoring to select most relevant messages
                relevant_history = self._select_relevant_messages(context.conversation_history, context)
                for msg in relevant_history:
                    # Only include assistant messages that are actual responses (not system messages)
                    if msg.get("role") in ["user", "assistant"] and msg.get("content"):
                        messages.append({
                            "role": msg["role"],
                            "content": msg["content"]
                        })
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            llm_start = time.time()
            llm = get_llm_by_type("basic")
            response = await llm.ainvoke(messages)
            logger.info(f"[TIMING] LLM invoke completed: {time.time() - llm_start:.2f}s")
            
            content = response.content if hasattr(response, 'content') else str(response)
            logger.info(f"PM plan LLM response: {content}")
            
            # Try to extract JSON
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                plan_data = json.loads(json_match.group())
                
                # Validate and return
                try:
                    pm_plan = PMPlan(**plan_data)
                    logger.info(f"Generated PM plan with {len(pm_plan.steps)} steps in {time.time() - plan_start:.2f}s")
                    # Use mode='json' to serialize enums as strings
                    return pm_plan.model_dump(mode='json')
                except Exception as validation_error:
                    logger.warning(f"PM plan validation failed: {validation_error}")
                    logger.warning(f"Plan data: {plan_data}")
                    return None
            
            return None
        except Exception as e:
            logger.error(f"Could not generate PM plan: {e} - {time.time() - plan_start:.2f}s")
            import traceback
            logger.error(f"Full error: {traceback.format_exc()}")
            return None
    
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
        user_query = "Create a Work Breakdown Structure for this project"
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
            
            # Check if there are additional tasks to execute (multi-step support)
            tasks = context.gathered_data.get("tasks")
            if tasks and isinstance(tasks, list) and len(tasks) > 1:
                # There are more tasks after WBS
                remaining_tasks = tasks[1:]  # Skip the first task which was WBS
                logger.info(f"Multi-step: Found {len(remaining_tasks)} additional tasks: {remaining_tasks}")
                
                # Execute additional tasks
                for task_description in remaining_tasks:
                    intent = self._detect_intent_from_task(task_description)
                    if intent and intent != IntentType.UNKNOWN:
                        logger.info(f"Multi-step: Executing {intent.value} for '{task_description}'")
                        # Update context for next intent
                        old_intent = context.intent
                        context.intent = intent
                        context.current_state = FlowState.EXECUTION_PHASE
                        
                        # Execute the next task using general execution handler
                        next_result = await self._execute_intent(intent, context)
                        if next_result.get("type") == "execution_completed":
                            result["message"] += f"\n\n✅ {next_result['message']}"
                        elif next_result.get("type") == "error":
                            result["message"] += f"\n\n❌ {next_result['message']}"
                        
                        # Reset intent for proper completion
                        context.intent = old_intent
        
        return result
    
    def _detect_intent_from_task(self, task_description: str) -> IntentType:
        """Detect intent from a task description string"""
        task_lower = task_description.lower()
        
        # Research / investigate
        if "research" in task_lower or "investigate" in task_lower:
            return IntentType.RESEARCH_TOPIC
        
        # Sprint planning
        elif "sprint" in task_lower and ("plan" in task_lower or "create" in task_lower):
            return IntentType.SPRINT_PLANNING
        
        # WBS creation
        elif "wbs" in task_lower or "work breakdown" in task_lower:
            return IntentType.CREATE_WBS
        
        # Report generation
        elif "report" in task_lower or "generate report" in task_lower:
            return IntentType.CREATE_REPORT
        
        # Project creation
        elif "create project" in task_lower or "new project" in task_lower:
            return IntentType.CREATE_PROJECT
        
        # Task planning
        elif "plan task" in task_lower or "task planning" in task_lower:
            return IntentType.PLAN_TASKS
        
        # Task breakdown
        elif "task breakdown" in task_lower or "breakdown" in task_lower:
            return IntentType.TASK_BREAKDOWN
        
        # Dependency analysis
        elif "dependency" in task_lower or "critical path" in task_lower:
            return IntentType.DEPENDENCY_ANALYSIS
        
        # Gantt chart
        elif "gantt" in task_lower or "timeline" in task_lower:
            return IntentType.GANTT_CHART
        
        # Status check
        elif "status" in task_lower or "progress" in task_lower:
            return IntentType.GET_STATUS
        
        # Task assignment
        elif "assign" in task_lower or "allocation" in task_lower:
            return IntentType.ASSIGN_TASKS
        
        # Resource check
        elif "resource" in task_lower or "capacity" in task_lower:
            return IntentType.CHECK_RESOURCES
        
        # Update project
        elif "update" in task_lower or "modify" in task_lower:
            return IntentType.UPDATE_PROJECT
        
        else:
            return IntentType.UNKNOWN
    
    async def _handle_sprint_planning_with_deerflow_planner(
        self,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Handle SPRINT_PLANNING using thinking plan"""
        # First, get thinking plan
        user_query = "Plan sprints for this project"
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
            
            # If still no project found, create one
            if project_name and not project:
                try:
                    from database.crud import create_project
                    from database.orm_models import Project
                    from uuid import uuid4
                    
                    logger.info(f"Auto-creating project '{project_name}' for WBS")
                    # Create project using the user_id from context
                    user_id = UUID("f430f348-d65f-427f-9379-3d0f163393d1")  # Mock user, TODO: get from context
                    
                    project = create_project(
                        db=self.db_session,
                        name=project_name,
                        description=project_description or "",
                        created_by=user_id,
                        domain=context.gathered_data.get("domain", "general")
                    )
                    project_id = str(project.id)
                    logger.info(f"Created project '{project_name}' with ID {project_id}")
                except Exception as e:
                    logger.error(f"Could not auto-create project: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            
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
            
            # Store project_id in gathered_data for multi-step workflows
            if project and project.id:
                context.gathered_data["project_id"] = str(project.id)
                logger.info(f"Stored project_id {str(project.id)} in context for multi-step workflows")
            
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
            
            # Initialize sprint planner with LLM
            from src.llms.llm import get_llm_by_type
            llm = get_llm_by_type("basic")
            planner = SprintPlanner(db_session=self.db_session, llm=llm)
            
            # Generate sprint plan
            sprint_plan = await planner.plan_sprint(
                project_id=project_id,
                sprint_name="",  # Let LLM generate the name
                duration_weeks=duration_weeks,
                team_capacity_hours_per_day=team_capacity
            )
            
            context.current_state = FlowState.COMPLETED
            
            # Use LLM-generated sprint name
            actual_sprint_name = sprint_plan.get('sprint_name', 'Sprint')
            
            return {
                "type": "execution_completed",
                "message": f"Sprint '{actual_sprint_name}' planned successfully! Assigned {sprint_plan['tasks_assigned']} tasks.",
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
            # Get report parameters
            project_id = context.gathered_data.get("project_id") or context.gathered_data.get("active_project_id")
            report_type = context.gathered_data.get("report_type", "status")
            
            if not project_id:
                return {
                    "type": "error",
                    "message": "Project ID is required to generate a report. Please specify which project or switch to one.",
                    "state": context.current_state.value
                }
            
            # Get project data
            project = await self.pm_provider.get_project(project_id)
            if not project:
                return {
                    "type": "error",
                    "message": f"Project not found.",
                    "state": context.current_state.value
                }
            
            # Get tasks
            tasks = await self.pm_provider.list_tasks(project_id=project_id)
            
            # Calculate metrics
            total_tasks = len(tasks)
            completed_tasks = sum(1 for t in tasks if t.status == "completed")
            in_progress_tasks = sum(1 for t in tasks if t.status == "in_progress")
            total_hours = sum(t.estimated_hours for t in tasks if t.estimated_hours)
            completed_hours = sum(
                t.estimated_hours for t in tasks 
                if t.estimated_hours and t.status == "completed"
            )
            
            # Generate report based on type
            if report_type == "progress":
                # Detailed progress report
                content = f"""# {project.name} - Progress Report

## Executive Summary
- **Status:** {project.status}
- **Total Tasks:** {total_tasks}
- **Completed:** {completed_tasks} ({(completed_tasks / total_tasks * 100) if total_tasks > 0 else 0:.1f}%)
- **In Progress:** {in_progress_tasks}
- **Overall Progress:** {(completed_hours / total_hours * 100) if total_hours > 0 else 0:.1f}% ({completed_hours:.1f}h / {total_hours:.1f}h)

## Task Details

### Completed Tasks ✅
{chr(10).join(f"- {t.title} ({t.estimated_hours}h)" if t.estimated_hours else f"- {t.title}" for t in tasks if t.status == "completed")}

### In Progress 🔄
{chr(10).join(f"- {t.title} ({t.estimated_hours}h)" if t.estimated_hours else f"- {t.title}" for t in tasks if t.status == "in_progress")}

### To Do ⏳
{chr(10).join(f"- {t.title} ({t.estimated_hours}h)" if t.estimated_hours else f"- {t.title}" for t in tasks if t.status not in ["completed", "in_progress"])}
"""
            else:
                # Status report (default)
                content = f"""# {project.name} - Status Report

## Current Status
- **Status:** {project.status or "Active"}
- **Total Tasks:** {total_tasks}
- **Completed:** {completed_tasks} ({(completed_tasks / total_tasks * 100) if total_tasks > 0 else 0:.1f}%)
- **In Progress:** {in_progress_tasks}
- **Progress:** {(completed_hours / total_hours * 100) if total_hours > 0 else 0:.1f}%

## Tasks
{chr(10).join(f"- {t.status or 'todo'}: {t.title}" for t in tasks)}
"""
            
            context.current_state = FlowState.COMPLETED
            return {
                "type": "execution_completed",
                "message": f"✅ **Report Generated Successfully**\n\nGenerated {report_type} report for '{project.name}':\n\n{content}",
                "state": context.current_state.value,
                "data": {
                    "report_type": report_type,
                    "project_name": project.name,
                    "total_tasks": total_tasks,
                    "completed_tasks": completed_tasks
                }
            }
        
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return {
                "type": "error",
                "message": f"Failed to generate report: {str(e)}",
                "state": context.current_state.value
            }
    
    async def _handle_task_assignment(
        self,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Handle TASK_ASSIGNMENT intent - Assign tasks to team members"""
        logger.info("Handling TASK_ASSIGNMENT intent")
        
        try:
            # Get parameters
            project_id = context.gathered_data.get("project_id") or context.gathered_data.get("active_project_id")
            task_ids = context.gathered_data.get("task_ids", [])
            assignee_id = context.gathered_data.get("assignee_id")
            assignee_name = context.gathered_data.get("assignee_name")
            
            if not project_id:
                return {
                    "type": "error",
                    "message": "Project context required. Please switch to a project first.",
                    "state": context.current_state.value
                }
            
            # Get assignee by name if provided
            if assignee_name and not assignee_id:
                users = await self.pm_provider.list_users(project_id=project_id)
                matching_user = next((u for u in users if u.name.lower() == assignee_name.lower()), None)
                if matching_user:
                    assignee_id = matching_user.id
                else:
                    return {
                        "type": "error",
                        "message": f"User '{assignee_name}' not found in project.",
                        "state": context.current_state.value
                    }
            
            # Get task IDs from context if not provided
            if not task_ids:
                # If we have specific task titles/names, fetch them
                task_titles = context.gathered_data.get("task_titles", [])
                if task_titles:
                    all_tasks = await self.pm_provider.list_tasks(project_id=project_id)
                    task_ids = [
                        t.id for t in all_tasks 
                        if any(title.lower() in t.title.lower() for title in task_titles)
                    ]
                else:
                    # Assign all unassigned tasks
                    all_tasks = await self.pm_provider.list_tasks(project_id=project_id)
                    task_ids = [t.id for t in all_tasks if not t.assignee_id]
            
            if not task_ids:
                return {
                    "type": "error",
                    "message": "No tasks found to assign.",
                    "state": context.current_state.value
                }
            
            if not assignee_id:
                return {
                    "type": "error",
                    "message": "Assignee is required. Please specify a user.",
                    "state": context.current_state.value
                }
            
            # Assign tasks
            assigned_count = 0
            for task_id in task_ids:
                try:
                    await self.pm_provider.update_task(task_id, {"assignee_id": assignee_id})
                    assigned_count += 1
                except Exception as e:
                    logger.warning(f"Failed to assign task {task_id}: {e}")
            
            # Get assignee name
            if assignee_name:
                assignee_display = assignee_name
            else:
                assignee = await self.pm_provider.get_user(assignee_id)
                assignee_display = assignee.name if assignee else assignee_id
            
            context.current_state = FlowState.COMPLETED
            return {
                "type": "execution_completed",
                "message": f"✅ **Tasks Assigned Successfully**\n\nAssigned {assigned_count} task(s) to {assignee_display}.",
                "state": context.current_state.value,
                "data": {
                    "assigned_count": assigned_count,
                    "assignee_id": assignee_id,
                    "task_ids": task_ids
                }
            }
        
        except Exception as e:
            logger.error(f"Task assignment failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "type": "error",
                "message": f"Failed to assign tasks: {str(e)}",
                "state": context.current_state.value
            }
    
    async def _handle_gantt_chart(
        self,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Handle GANTT_CHART intent - Generate timeline/Gantt view"""
        logger.info("Handling GANTT_CHART intent")
        
        try:
            # Get project
            project_id = context.gathered_data.get("project_id") or context.gathered_data.get("active_project_id")
            if not project_id:
                return {
                    "type": "error",
                    "message": "Project context required. Please switch to a project first.",
                    "state": context.current_state.value
                }
            
            # Get tasks
            tasks = await self.pm_provider.list_tasks(project_id=project_id)
            
            # Build timeline view
            if not tasks:
                return {
                    "type": "execution_completed",
                    "message": "✅ **Timeline View**\n\nNo tasks found for this project.",
                    "state": "complete"
                }
            
            # Group tasks by status
            completed = [t for t in tasks if t.status == "completed"]
            in_progress = [t for t in tasks if t.status == "in_progress"]
            todo = [t for t in tasks if t.status not in ["completed", "in_progress"]]
            
            # Build timeline content
            content = f"""# Project Timeline

## Tasks by Status

### ✅ Completed ({len(completed)})
{chr(10).join(f"- {t.title} {f'({t.estimated_hours}h)' if t.estimated_hours else ''}" for t in completed)}

### 🔄 In Progress ({len(in_progress)})
{chr(10).join(f"- {t.title} {f'({t.estimated_hours}h)' if t.estimated_hours else ''}" for t in in_progress)}

### ⏳ To Do ({len(todo)})
{chr(10).join(f"- {t.title} {f'({t.estimated_hours}h)' if t.estimated_hours else ''}" for t in todo)}
"""
            
            context.current_state = FlowState.COMPLETED
            return {
                "type": "execution_completed",
                "message": f"✅ **Timeline View Generated**\n\n{content}",
                "state": context.current_state.value,
                "data": {
                    "total_tasks": len(tasks),
                    "completed": len(completed),
                    "in_progress": len(in_progress),
                    "todo": len(todo)
                }
            }
        
        except Exception as e:
            logger.error(f"Gantt chart generation failed: {e}")
            return {
                "type": "error",
                "message": f"Failed to generate timeline view: {str(e)}",
                "state": context.current_state.value
            }
    
    async def _handle_switch_project(
        self,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Handle SWITCH_PROJECT intent - Set the active project context"""
        logger.info("Handling SWITCH_PROJECT intent")
        
        try:
            project_id = context.gathered_data.get("project_id")
            project_name = context.gathered_data.get("project_name")
            
            # If project_id not provided, try to find by project_name
            if not project_id:
                if project_name:
                    # Search for project by name
                    all_projects = await self.pm_provider.list_projects()
                    matching_projects = [p for p in all_projects if p.name.lower() == project_name.lower()]
                    
                    if len(matching_projects) == 0:
                        return {
                            "type": "error",
                            "message": f"Project '{project_name}' not found.",
                            "state": context.current_state.value
                        }
                    elif len(matching_projects) > 1:
                        return {
                            "type": "error",
                            "message": f"Multiple projects found with name '{project_name}'. Please specify project ID.",
                            "state": context.current_state.value
                        }
                    else:
                        project_id = str(matching_projects[0].id)
                        project_name = matching_projects[0].name
                        logger.info(f"Found project '{project_name}' with ID: {project_id}")
                else:
                    return {
                        "type": "error",
                        "message": "Project ID or name is required to switch project. Please specify which project.",
                        "state": context.current_state.value
                    }
            else:
                # Get project to retrieve name
                project = await self.pm_provider.get_project(project_id)
                if not project:
                    return {
                        "type": "error",
                        "message": f"Project with ID {project_id} not found.",
                        "state": context.current_state.value
                    }
                project_name = project.name
            
            # Store active project in context for future commands
            context.gathered_data['active_project_id'] = project_id
            context.gathered_data['active_project_name'] = project_name
            
            # Reset state to INTENT_DETECTION so next message can process normally
            context.current_state = FlowState.INTENT_DETECTION
            
            return {
                "type": "execution_completed",
                "message": f"✅ Switched to project: **{project_name}** (ID: `{project_id}`)\n\nNow I'll use this project as the default for all your commands. You can ask me to:\n- List tasks: 'show all tasks'\n- List sprints: 'list sprints'\n- Check status: 'what's the status?'\n- Update tasks: 'mark task X as done'",
                "state": "complete",
                "data": {
                    "project_id": project_id,
                    "project_name": project_name
                }
            }
        
        except Exception as e:
            logger.error(f"Switch project failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "type": "error",
                "message": f"Failed to switch project: {str(e)}",
                "state": context.current_state.value
            }
    
    async def _handle_switch_sprint(
        self,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Handle SWITCH_SPRINT intent - Set the active sprint context"""
        logger.info("Handling SWITCH_SPRINT intent")
        
        try:
            # Get active project first
            project_id = context.gathered_data.get("active_project_id")
            if not project_id:
                return {
                    "type": "error",
                    "message": "Please switch to a project first before selecting a sprint.",
                    "state": context.current_state.value
                }
            
            sprint_id = context.gathered_data.get("sprint_id")
            sprint_name = context.gathered_data.get("sprint_name")
            
            # If sprint_id not provided, try to find by sprint_name
            if not sprint_id:
                if sprint_name:
                    # Search for sprint by name within the project
                    all_sprints = await self.pm_provider.list_sprints(project_id=project_id)
                    matching_sprints = [s for s in all_sprints if s.name and s.name.lower() == sprint_name.lower()]
                    
                    if len(matching_sprints) == 0:
                        return {
                            "type": "error",
                            "message": f"Sprint '{sprint_name}' not found in this project.",
                            "state": context.current_state.value
                        }
                    elif len(matching_sprints) > 1:
                        return {
                            "type": "error",
                            "message": f"Multiple sprints found with name '{sprint_name}'. Please specify sprint ID.",
                            "state": context.current_state.value
                        }
                    else:
                        sprint_id = str(matching_sprints[0].id)
                        sprint_name = matching_sprints[0].name
                        logger.info(f"Found sprint '{sprint_name}' with ID: {sprint_id}")
                else:
                    return {
                        "type": "error",
                        "message": "Sprint ID or name is required to switch sprint. Please specify which sprint.",
                        "state": context.current_state.value
                    }
            
            # Store active sprint in context for future commands
            context.gathered_data['active_sprint_id'] = sprint_id
            context.gathered_data['active_sprint_name'] = sprint_name
            
            # Reset state to INTENT_DETECTION so next message can process normally
            context.current_state = FlowState.INTENT_DETECTION
            
            return {
                "type": "execution_completed",
                "message": f"✅ Switched to sprint: **{sprint_name}** (ID: `{sprint_id}`)\n\nNow I'll use this sprint as the default for all your commands. You can ask me to:\n- List tasks in sprint: 'show tasks'\n- Check sprint status: 'what's the sprint status?'\n- Update sprint: 'extend sprint by 3 days'",
                "state": "complete",
                "data": {
                    "sprint_id": sprint_id,
                    "sprint_name": sprint_name
                }
            }
        
        except Exception as e:
            logger.error(f"Switch sprint failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "type": "error",
                "message": f"Failed to switch sprint: {str(e)}",
                "state": context.current_state.value
            }
    
    async def _handle_switch_task(
        self,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Handle SWITCH_TASK intent - Set the active task context"""
        logger.info("Handling SWITCH_TASK intent")
        
        try:
            # Get active project first
            project_id = context.gathered_data.get("active_project_id")
            if not project_id:
                return {
                    "type": "error",
                    "message": "Please switch to a project first before selecting a task.",
                    "state": context.current_state.value
                }
            
            task_id = context.gathered_data.get("task_id")
            task_title = context.gathered_data.get("task_title")
            
            # If task_id not provided, try to find by task_title
            if not task_id:
                if task_title:
                    # Search for task by title within the project
                    all_tasks = await self.pm_provider.list_tasks(project_id=project_id)
                    matching_tasks = [t for t in all_tasks if t.title and t.title.lower() == task_title.lower()]
                    
                    if len(matching_tasks) == 0:
                        return {
                            "type": "error",
                            "message": f"Task '{task_title}' not found in this project.",
                            "state": context.current_state.value
                        }
                    elif len(matching_tasks) > 1:
                        return {
                            "type": "error",
                            "message": f"Multiple tasks found with title '{task_title}'. Please specify task ID.",
                            "state": context.current_state.value
                        }
                    else:
                        task_id = str(matching_tasks[0].id)
                        task_title = matching_tasks[0].title
                        logger.info(f"Found task '{task_title}' with ID: {task_id}")
                else:
                    return {
                        "type": "error",
                        "message": "Task ID or title is required to switch task. Please specify which task.",
                        "state": context.current_state.value
                    }
            
            # Get full task details
            task = await self.pm_provider.get_task(task_id)
            if not task:
                return {
                    "type": "error",
                    "message": f"Task with ID {task_id} not found.",
                    "state": context.current_state.value
                }
            
            # Store active task in context for future commands
            context.gathered_data['active_task_id'] = task_id
            context.gathered_data['active_task_title'] = task.title
            
            # Reset state to INTENT_DETECTION so next message can process normally
            context.current_state = FlowState.INTENT_DETECTION
            
            # Build task details message
            status = getattr(task, 'status', 'unknown')
            priority = getattr(task, 'priority', 'medium')
            hours = getattr(task, 'estimated_hours', None)
            priority_emoji = "🔴" if priority == "high" else "🟡" if priority == "medium" else "🟢"
            hours_text = f"{hours}h" if hours else "N/A"
            
            return {
                "type": "execution_completed",
                "message": f"✅ Switched to task: **{task.title}** (ID: `{task_id}`)\n\n**Task Details:**\n- Status: {status}\n- Priority: {priority_emoji} {priority}\n- Estimated: {hours_text}\n\nNow you can discuss this task in detail. You can ask me to:\n- Update status: 'mark as in progress'\n- Change priority: 'set to high priority'\n- Update time: 'estimate 8 hours'\n- Add details: 'add description of implementation approach'",
                "state": "complete",
                "data": {
                    "task_id": task_id,
                    "task_title": task.title,
                    "task": {
                        "status": status,
                        "priority": priority,
                        "estimated_hours": hours
                    }
                }
            }
        
        except Exception as e:
            logger.error(f"Switch task failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "type": "error",
                "message": f"Failed to switch task: {str(e)}",
                "state": context.current_state.value
            }
    
    async def _handle_list_projects(
        self,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Handle LIST_PROJECTS intent - List all projects"""
        logger.info("Handling LIST_PROJECTS intent")
        
        try:
            # Use PM provider (OpenProject, JIRA, etc.)
            pm_projects = await self.pm_provider.list_projects()
            projects = pm_projects
            
            context.current_state = FlowState.COMPLETED
            
            # Format message with project list
            message_parts = [f"Found **{len(projects)}** projects:\n"]
            for i, project in enumerate(projects, 1):
                message_parts.append(
                    f"{i}. **{project.name}**\n"
                    f"   - ID: `{project.id}`\n"
                    f"   - Description: {project.description or 'N/A'}\n"
                )
            
            return {
                "type": "execution_completed",
                "message": "\n".join(message_parts),
                "state": context.current_state.value,
                "data": {
                    "projects_count": len(projects),
                    "projects": [
                        {
                            "id": str(project.id) if hasattr(project, 'id') else None,
                            "name": project.name,
                            "description": project.description
                        }
                        for project in projects
                    ]
                }
            }
        
        except Exception as e:
            logger.error(f"List projects failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "type": "error",
                "message": f"Failed to list projects: {str(e)}",
                "state": context.current_state.value
            }
    
    async def _handle_list_tasks(
        self,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Handle LIST_TASKS intent - List tasks for a project"""
        logger.info("Handling LIST_TASKS intent")
        
        try:
            project_id = context.gathered_data.get("project_id")
            project_name = context.gathered_data.get("project_name")
            
            # If project_id not provided, try to find by project_name or use active project
            if not project_id:
                if project_name:
                    # Search for project by name
                    all_projects = await self.pm_provider.list_projects()
                    matching_projects = [p for p in all_projects if p.name.lower() == project_name.lower()]
                    
                    if len(matching_projects) == 0:
                        return {
                            "type": "error",
                            "message": f"Project '{project_name}' not found.",
                            "state": context.current_state.value
                        }
                    elif len(matching_projects) > 1:
                        return {
                            "type": "error",
                            "message": f"Multiple projects found with name '{project_name}'. Please specify project ID.",
                            "state": context.current_state.value
                        }
                    else:
                        project_id = str(matching_projects[0].id)
                        logger.info(f"Found project '{project_name}' with ID: {project_id}")
                elif context.gathered_data.get("active_project_id"):
                    # Use active project from context
                    project_id = context.gathered_data.get("active_project_id")
                    logger.info(f"Using active project ID: {project_id}")
                else:
                    return {
                        "type": "error",
                        "message": "Project ID or name is required to list tasks. Please specify which project, or switch to a project first.",
                        "state": context.current_state.value
                    }
            
            # Use PM provider (OpenProject, JIRA, etc.)
            project = await self.pm_provider.get_project(project_id)
            if not project:
                return {
                    "type": "error",
                    "message": f"Project with ID {project_id} not found.",
                    "state": context.current_state.value
                }
            
            pm_tasks = await self.pm_provider.list_tasks(project_id=project_id)
            tasks = pm_tasks
            project_name = project.name
            
            context.current_state = FlowState.COMPLETED
            
            # Format message with task list
            message_parts = [f"Found **{len(tasks)}** tasks for project '{project_name}':\n"]
            for i, task in enumerate(tasks, 1):
                priority_emoji = "🔴" if task.priority == "high" else "🟡" if task.priority == "medium" else "🟢"
                hours_text = f"{task.estimated_hours}h" if task.estimated_hours else "N/A"
                status = task.status if hasattr(task, 'status') else None
                title = task.title
                message_parts.append(
                    f"{i}. **{title}**\n"
                    f"   - Status: {status or 'N/A'}\n"
                    f"   - Priority: {priority_emoji} {task.priority or 'medium'}\n"
                    f"   - Estimated: {hours_text}\n"
                )
            
            return {
                "type": "execution_completed",
                "message": "\n".join(message_parts),
                "state": context.current_state.value,
                "data": {
                    "project_name": project_name,
                    "tasks_count": len(tasks),
                    "tasks": [
                        {
                            "id": str(task.id) if hasattr(task, 'id') else None,
                            "title": task.title,
                            "status": task.status if hasattr(task, 'status') else None,
                            "priority": task.priority if hasattr(task, 'priority') else None,
                            "estimated_hours": task.estimated_hours if hasattr(task, 'estimated_hours') else None
                        }
                        for task in tasks
                    ]
                }
            }
        
        except Exception as e:
            logger.error(f"List tasks failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "type": "error",
                "message": f"Failed to list tasks: {str(e)}",
                "state": context.current_state.value
            }
    
    async def _handle_list_my_tasks(
        self,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Handle LIST_MY_TASKS intent - List all tasks assigned to current user"""
        logger.info("Handling LIST_MY_TASKS intent")
        
        try:
            # Get user_id from context (set by process_message)
            # Default to mock user for now, but should come from auth in production
            user_id = context.gathered_data.get("user_id", "f430f348-d65f-427f-9379-3d0f163393d1")
            
            # For OpenProject, we need to map our user_id to OpenProject user_id
            # This is a simplified approach - in production, use proper user mapping
            # For now, try to get current user from OpenProject API
            openproject_user_id = None
            
            # Get the current user from the PM provider (must succeed for user-specific queries)
            try:
                current_user = await self.pm_provider.get_current_user()
                if not current_user:
                    return {
                        "type": "error",
                        "message": "Cannot determine the current user. Please ensure you are properly authenticated with a valid API key.",
                        "state": context.current_state.value
                    }
                
                openproject_user_id = str(current_user.id)
                logger.info(f"Using current user from API key: {current_user.name} (ID: {openproject_user_id})")
            except Exception as e:
                logger.error(f"Could not fetch current user from PM provider: {e}")
                return {
                    "type": "error",
                    "message": f"Authentication error: Could not identify the current user. {str(e)}",
                    "state": context.current_state.value
                }
            
            # Query tasks filtered by assignee
            pm_tasks = await self.pm_provider.list_tasks(assignee_id=openproject_user_id)
            tasks = pm_tasks
            
            # Filter by date if requested (week, month, etc.)
            # Check if context has date filters from user message
            filter_by_week = context.gathered_data.get("filter_week")
            filter_by_date = context.gathered_data.get("filter_date")
            period = context.gathered_data.get("period", "")
            
            # Convert period text to filter_week if needed
            if not filter_by_week and period:
                period_lower = period.lower()
                if "tuần này" in period_lower or "this week" in period_lower or "current week" in period_lower:
                    filter_by_week = True
                    logger.info(f"Detected week filter from period: {period}")
            
            if filter_by_week or filter_by_date:
                from datetime import datetime, timedelta, date
                
                if filter_by_week:
                    # Get current week start (Monday) and end (Sunday)
                    today = datetime.now().date()
                    start_of_week = today - timedelta(days=today.weekday())
                    end_of_week = start_of_week + timedelta(days=6)
                    logger.info(f"Filtering by current week: {start_of_week} to {end_of_week}")
                else:
                    # Use provided date range
                    start_of_week = filter_by_date.get("start")
                    end_of_week = filter_by_date.get("end")
                    logger.info(f"Filtering by date range: {start_of_week} to {end_of_week}")
                
                if start_of_week and end_of_week:
                    filtered_tasks = []
                    for task in tasks:
                        # Task falls within week if start_date <= week_end OR due_date >= week_start
                        task_start = task.start_date if hasattr(task, 'start_date') else None
                        task_due = task.due_date if hasattr(task, 'due_date') else None
                        
                        if task_start and task_start <= end_of_week:
                            filtered_tasks.append(task)
                        elif task_due and task_due >= start_of_week:
                            filtered_tasks.append(task)
                    
                    tasks = filtered_tasks
                    logger.info(f"Filtered to {len(tasks)} tasks in week {start_of_week} to {end_of_week}")
            
            # If no tasks found, return empty result (don't show all tasks)
            if not tasks:
                return {
                    "type": "execution_completed",
                    "message": "Found **0** tasks assigned to you.",
                    "state": "complete",
                    "data": {
                        "tasks_count": 0,
                        "tasks": []
                    }
                }
            
            # Group tasks by project for better organization
            from collections import defaultdict
            tasks_by_project = defaultdict(list)
            for task in tasks:
                project_id = task.project_id or "unassigned"
                tasks_by_project[project_id].append(task)
            
            # Build formatted message
            total_tasks = len(tasks)
            
            # Calculate total hours for workload
            total_hours = 0.0
            for task in tasks:
                if hasattr(task, 'estimated_hours') and task.estimated_hours:
                    total_hours += float(task.estimated_hours)
            
            logger.info(f"Calculated total hours: {total_hours} from {total_tasks} tasks")
            
            if filter_by_week or filter_by_date:
                message_parts = [f"📊 **Your workload for this period:**\n"]
                message_parts.append(f"- **{total_tasks}** tasks\n")
                if total_hours > 0:
                    message_parts.append(f"- **{total_hours:.1f}** hours total\n")
                else:
                    message_parts.append(f"- **No time estimates** available\n")
                message_parts.append("\n**Tasks:**\n")
            else:
                message_parts = [f"Found **{total_tasks}** tasks assigned to you:\n"]
            
            if len(tasks_by_project) == 1 and total_tasks > 0:
                # All tasks in one project
                project_id = list(tasks_by_project.keys())[0]
                project_tasks = tasks_by_project[project_id]
                
                # Get project name
                if project_id != "unassigned":
                    project = await self.pm_provider.get_project(project_id)
                    project_name = project.name if project else project_id
                else:
                    project_name = "Unassigned"
                
                message_parts.append(f"All tasks are in **{project_name}**:\n")
                for i, task in enumerate(project_tasks[:15], 1):  # Limit display
                    priority_emoji = "🔴" if task.priority == "high" else "🟡" if task.priority == "medium" else "🟢"
                    hours_text = f"{task.estimated_hours}h" if task.estimated_hours else "N/A"
                    status = task.status if hasattr(task, 'status') else 'N/A'
                    message_parts.append(
                        f"{i}. **{task.title}**\n"
                        f"   - Status: {status}\n"
                        f"   - Priority: {priority_emoji} {task.priority or 'medium'}\n"
                        f"   - Estimated: {hours_text}\n"
                    )
            else:
                # Tasks across multiple projects
                for project_id, project_tasks in list(tasks_by_project.items())[:5]:  # Limit to 5 projects
                    if project_id != "unassigned":
                        project = await self.pm_provider.get_project(project_id)
                        project_name = project.name if project else project_id
                    else:
                        project_name = "Unassigned"
                    
                    message_parts.append(f"\n**{project_name}** ({len(project_tasks)} tasks):\n")
                    for task in project_tasks[:5]:  # Limit 5 tasks per project
                        priority_emoji = "🔴" if task.priority == "high" else "🟡" if task.priority == "medium" else "🟢"
                        hours_text = f"{task.estimated_hours}h" if task.estimated_hours else "No ETA"
                        message_parts.append(f"- **{task.title}** ({priority_emoji} {task.priority or 'medium'}) - ETA: {hours_text}\n")
            
            if total_tasks > 20:
                message_parts.append(f"\n_Showing first 20 tasks. Total: {total_tasks}_")
            
            context.current_state = FlowState.COMPLETED
            
            return {
                "type": "execution_completed",
                "message": "\n".join(message_parts),
                "state": "complete",
                "data": {
                    "tasks_count": total_tasks,
                    "tasks": [
                        {
                            "id": str(task.id) if hasattr(task, 'id') else None,
                            "title": task.title,
                            "status": task.status if hasattr(task, 'status') else None,
                            "priority": task.priority if hasattr(task, 'priority') else None
                        }
                        for task in tasks[:20]
                    ]
                }
            }
        
        except Exception as e:
            logger.error(f"List my tasks failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "type": "error",
                "message": f"Failed to list your tasks: {str(e)}",
                "state": context.current_state.value
            }
    
    async def _handle_list_sprints(
        self,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Handle LIST_SPRINTS intent - List sprints for a project"""
        logger.info("Handling LIST_SPRINTS intent")
        
        try:
            project_id = context.gathered_data.get("project_id")
            project_name = context.gathered_data.get("project_name")
            
            # If project_id not provided, try to find by project_name
            if not project_id:
                if project_name:
                    # Search for project by name
                    all_projects = await self.pm_provider.list_projects()
                    matching_projects = [p for p in all_projects if p.name.lower() == project_name.lower()]
                    
                    if len(matching_projects) == 0:
                        return {
                            "type": "error",
                            "message": f"Project '{project_name}' not found.",
                            "state": context.current_state.value
                        }
                    elif len(matching_projects) > 1:
                        return {
                            "type": "error",
                            "message": f"Multiple projects found with name '{project_name}'. Please specify project ID.",
                            "state": context.current_state.value
                        }
                    else:
                        project_id = str(matching_projects[0].id)
                        logger.info(f"Found project '{project_name}' with ID: {project_id}")
                elif context.gathered_data.get("active_project_id"):
                    # Use active project from context
                    project_id = context.gathered_data.get("active_project_id")
                    logger.info(f"Using active project ID: {project_id}")
                else:
                    return {
                        "type": "error",
                        "message": "Project ID or name is required to list sprints. Please specify which project, or switch to a project first.",
                        "state": context.current_state.value
                    }
            
            # Use PM provider (OpenProject, JIRA, etc.)
            project = await self.pm_provider.get_project(project_id)
            if not project:
                return {
                    "type": "error",
                    "message": f"Project with ID {project_id} not found.",
                    "state": context.current_state.value
                }
            
            pm_sprints = await self.pm_provider.list_sprints(project_id=project_id)
            sprints = pm_sprints
            project_name = project.name
            
            context.current_state = FlowState.COMPLETED
            
            # Format message with sprint list
            message_parts = [f"Found **{len(sprints)}** sprints for project '{project_name}':\n"]
            for i, sprint in enumerate(sprints, 1):
                # Handle both DB and PM models
                utilization = getattr(sprint, 'utilization', 0) or 0
                utilization_emoji = "🟢" if utilization < 70 else "🟡" if utilization < 90 else "🔴"
                status = getattr(sprint, 'status', 'unknown')
                name = sprint.name if hasattr(sprint, 'name') else str(sprint.id)
                capacity = getattr(sprint, 'capacity_hours', 0) or 0
                planned = getattr(sprint, 'planned_hours', 0) or 0
                
                message_parts.append(
                    f"{i}. **{name}**\n"
                    f"   - Status: {status}\n"
                    f"   - Capacity: {capacity:.0f}h\n"
                    f"   - Planned: {planned:.0f}h\n"
                    f"   - Utilization: {utilization_emoji} {utilization:.0f}%\n"
                )
            
            return {
                "type": "execution_completed",
                "message": "\n".join(message_parts),
                "state": context.current_state.value,
                "data": {
                    "project_name": project_name,
                    "sprints_count": len(sprints),
                    "sprints": [
                        {
                            "id": str(getattr(sprint, 'id', i)),
                            "name": getattr(sprint, 'name', 'Unknown'),
                            "status": getattr(sprint, 'status', 'unknown'),
                            "capacity_hours": getattr(sprint, 'capacity_hours', 0),
                            "planned_hours": getattr(sprint, 'planned_hours', 0),
                            "utilization": getattr(sprint, 'utilization', 0)
                        }
                        for i, sprint in enumerate(sprints)
                    ]
                }
            }
        
        except Exception as e:
            logger.error(f"List sprints failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "type": "error",
                "message": f"Failed to list sprints: {str(e)}",
                "state": context.current_state.value
            }
    
    async def _handle_get_project_status(
        self,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Handle GET_PROJECT_STATUS intent - Get status of a project"""
        logger.info("Handling GET_PROJECT_STATUS intent")
        
        try:
            project_id = context.gathered_data.get("project_id")
            project_name = context.gathered_data.get("project_name")
            
            # If project_id not provided, try to find by project_name
            if not project_id:
                if project_name:
                    # Search for project by name
                    all_projects = await self.pm_provider.list_projects()
                    matching_projects = [p for p in all_projects if p.name.lower() == project_name.lower()]
                    
                    if len(matching_projects) == 0:
                        return {
                            "type": "error",
                            "message": f"Project '{project_name}' not found.",
                            "state": context.current_state.value
                        }
                    elif len(matching_projects) > 1:
                        return {
                            "type": "error",
                            "message": f"Multiple projects found with name '{project_name}'. Please specify project ID.",
                            "state": context.current_state.value
                        }
                    else:
                        project_id = str(matching_projects[0].id)
                        logger.info(f"Found project '{project_name}' with ID: {project_id}")
                elif context.gathered_data.get("active_project_id"):
                    # Use active project from context
                    project_id = context.gathered_data.get("active_project_id")
                    logger.info(f"Using active project ID: {project_id}")
                else:
                    return {
                        "type": "error",
                        "message": "Project ID or name is required. Please specify which project, or switch to a project first.",
                        "state": context.current_state.value
                    }
            
            # Use PM provider (OpenProject, JIRA, etc.)
            project = await self.pm_provider.get_project(project_id)
            if not project:
                return {
                    "type": "error",
                    "message": f"Project with ID {project_id} not found.",
                    "state": context.current_state.value
                }
            
            # Get tasks and sprints counts
            tasks = await self.pm_provider.list_tasks(project_id=project_id)
            sprints = await self.pm_provider.list_sprints(project_id=project_id)
            
            # Count tasks by status
            tasks_by_status = {}
            for task in tasks:
                status = task.status if hasattr(task, 'status') else 'unknown'
                tasks_by_status[status] = tasks_by_status.get(status, 0) + 1
            
            context.current_state = FlowState.COMPLETED
            
            # Format message with project status
            project_status = project.status if hasattr(project, 'status') else 'unknown'
            status_emoji = {
                'completed': '✅',
                'in_progress': '🚀',
                'planned': '📋',
                'blocked': '⚠️',
                'cancelled': '❌'
            }.get(project_status, '📊')
            
            message_parts = [
                f"## Project Status: **{project.name}**\n",
                f"{status_emoji} **Overall Status:** {project_status}\n",
                f"\n📊 **Summary:**\n",
                f"- Total Tasks: **{len(tasks)}**\n",
                f"- Total Sprints: **{len(sprints)}**\n"
            ]
            
            if tasks_by_status:
                message_parts.append(f"\n📋 **Tasks by Status:**\n")
                for status, count in sorted(tasks_by_status.items()):
                    message_parts.append(f"- {status}: **{count}**\n")
            
            return {
                "type": "execution_completed",
                "message": "".join(message_parts),
                "state": context.current_state.value,
                "data": {
                    "project_name": project.name,
                    "status": project_status,
                    "tasks_count": len(tasks),
                    "tasks_by_status": tasks_by_status,
                    "sprints_count": len(sprints)
                }
            }
        
        except Exception as e:
            logger.error(f"Get project status failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "type": "error",
                "message": f"Failed to get project status: {str(e)}",
                "state": context.current_state.value
            }
    
    async def _handle_eta_research(
        self,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Handle ETA research - Research and estimate time for tasks without ETA"""
        logger.info("Handling ETA research")
        
        try:
            # Get current user's tasks
            current_user = await self.pm_provider.get_current_user()
            if not current_user:
                return {
                    "type": "error",
                    "message": "Cannot determine current user for ETA research.",
                    "state": context.current_state.value
                }
            
            # List all user's tasks
            all_tasks = await self.pm_provider.list_tasks(assignee_id=str(current_user.id))
            
            # Filter tasks without ETA
            tasks_without_eta = [
                task for task in all_tasks
                if not task.estimated_hours or task.estimated_hours == 0
            ]
            
            if not tasks_without_eta:
                context.current_state = FlowState.COMPLETED
                return {
                    "type": "execution_completed",
                    "message": "✅ All your tasks already have ETA estimates!",
                    "state": "complete"
                }
            
            # Process tasks in batches to avoid LLM token limits
            # Limit to 20 tasks per batch for reliable LLM responses
            batch_size = 20
            total_batches = (len(tasks_without_eta) + batch_size - 1) // batch_size
            
            # Process all batches automatically
            all_estimates = {}
            total_updated = 0
            batch_results = []
            
            from src.llms.llm import get_llm_by_type
            llm = get_llm_by_type("basic")
            import re
            
            for batch_num in range(total_batches):
                # Get tasks for this batch
                start_idx = batch_num * batch_size
                end_idx = start_idx + batch_size
                tasks_batch = tasks_without_eta[start_idx:end_idx]
                
                logger.info(f"Processing batch {batch_num + 1}/{total_batches} with {len(tasks_batch)} tasks")
                
                # Build research query for LLM
                task_list = "\n".join([
                    f"- {task.title} (ID: {task.id})"
                    for task in tasks_batch
                ])
                
                research_query = f"""Please estimate the time needed for each of these tasks in hours:

{task_list}

For each task, provide your estimate in hours based on typical effort for similar tasks. Consider complexity, dependencies, and typical industry standards. Respond in a format like:
- Task Title (ID: x): Y hours

Be concise but realistic."""
                
                # Call LLM for estimates
                response = await llm.ainvoke(research_query)
                
                if isinstance(response, str):
                    llm_response = response
                else:
                    llm_response = response.content if hasattr(response, 'content') else str(response)
                
                logger.info(f"LLM ETA response batch {batch_num + 1}: {llm_response[:200]}...")
                
                # Parse estimates from LLM response
                batch_estimates = {}
                for task in tasks_batch:
                    pattern_id = rf".*\(ID:\s*{task.id}\)[:\s]*(\d+(?:\.\d+)?)\s*hours?"
                    pattern_title = rf".*{re.escape(task.title)}[:\s]*(\d+(?:\.\d+)?)\s*hours?"
                    
                    match = re.search(pattern_id, llm_response, re.IGNORECASE) or \
                           re.search(pattern_title, llm_response, re.IGNORECASE)
                    if match:
                        hours = float(match.group(1))
                        batch_estimates[task.id] = hours
                        logger.info(f"Parsed ETA for {task.title}: {hours}h")
                
                all_estimates.update(batch_estimates)
                
                # Update tasks with estimates
                batch_updated = 0
                for task_id, hours in batch_estimates.items():
                    try:
                        logger.info(f"Updating task {task_id} with {hours}h")
                        await self.pm_provider.update_task(task_id, {"estimated_hours": hours})
                        batch_updated += 1
                        logger.info(f"Successfully updated task {task_id}")
                    except Exception as e:
                        logger.error(f"Failed to update task {task_id}: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                
                total_updated += batch_updated
                batch_results.append({
                    "batch": batch_num + 1,
                    "total_batches": total_batches,
                    "tasks_processed": len(tasks_batch),
                    "updated": batch_updated
                })
            
            context.current_state = FlowState.COMPLETED
            
            message_parts = [
                f"✅ **ETA Research Completed**\n",
                f"Processed {total_batches} batch(es) automatically\n",
                f"Analyzed {len(tasks_without_eta)} tasks in total\n",
                f"Updated {total_updated} tasks with new estimates\n"
            ]
            
            if total_updated > 0:
                message_parts.append("\n**Sample Updated Tasks:**\n")
                # Show first 10 updated tasks as sample
                sample_shown = 0
                for task_id, hours in list(all_estimates.items()):
                    if sample_shown >= 10:
                        break
                    task = next((t for t in tasks_without_eta if t.id == task_id), None)
                    if task:
                        message_parts.append(f"- {task.title}: **{hours}h**\n")
                        sample_shown += 1
                
                if total_updated > 10:
                    message_parts.append(f"\n_... and {total_updated - 10} more tasks_\n")
            
            return {
                "type": "execution_completed",
                "message": "".join(message_parts),
                "state": "complete",
                "data": {
                    "analyzed_tasks": len(tasks_without_eta),
                    "updated_tasks": total_updated,
                    "estimates": all_estimates,
                    "batches": batch_results
                }
            }
        
        except Exception as e:
            logger.error(f"ETA research failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "type": "error",
                "message": f"Failed to research ETA: {str(e)}",
                "state": context.current_state.value
            }
    
    async def _handle_generic_research(
        self,
        context: ConversationContext,
        step: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle generic research step - Use LLM to answer research questions"""
        logger.info(f"Handling generic research: {step.get('title')}")
        
        try:
            title = step.get('title', '')
            description = step.get('description', '')
            
            # Build research query from step description
            research_query = f"""{description}

Please provide a comprehensive analysis or answer. Be specific and actionable."""
            
            # Call LLM for research
            from src.llms.llm import get_llm_by_type
            llm = get_llm_by_type("basic")
            response = await llm.ainvoke(research_query)
            
            if isinstance(response, str):
                research_result = response
            else:
                research_result = response.content if hasattr(response, 'content') else str(response)
            
            logger.info(f"Generic research completed: {len(research_result)} chars")
            
            context.current_state = FlowState.COMPLETED
            
            return {
                "type": "execution_completed",
                "message": f"✅ **Research Completed: {title}**\n\n{research_result}",
                "state": "complete"
            }
        
        except Exception as e:
            logger.error(f"Generic research failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "type": "error",
                "message": f"Failed to complete research: {str(e)}",
                "state": context.current_state.value
            }
    
    async def _handle_dependency_research(
        self,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Handle dependency analysis research - Analyze task dependencies"""
        logger.info("Handling dependency research")
        
        try:
            # Get current project context
            project_id = context.gathered_data.get("project_id") or context.gathered_data.get("active_project_id")
            if not project_id:
                return {
                    "type": "error",
                    "message": "Project context required for dependency analysis. Please switch to a project first.",
                    "state": context.current_state.value
                }
            
            # List all tasks for the project
            all_tasks = await self.pm_provider.list_tasks(project_id=project_id)
            
            if not all_tasks:
                return {
                    "type": "error",
                    "message": "No tasks found for dependency analysis.",
                    "state": context.current_state.value
                }
            
            # Build task dependency query for LLM
            task_list = "\n".join([
                f"- {task.title} (ID: {task.id}, Priority: {task.priority or 'medium'})"
                for task in all_tasks[:20]  # Limit to 20 tasks
            ])
            
            research_query = f"""Analyze dependencies between these project tasks:

{task_list}

For each task, identify:
1. Tasks it depends on (prerequisites)
2. Tasks that depend on it (blockers)
3. Critical path considerations

Return a concise dependency analysis in this format:
- Task Name: Depends on [list], Blocks [list]"""
            
            # Call LLM for dependency analysis
            from src.llms.llm import get_llm_by_type
            llm = get_llm_by_type("basic")
            response = await llm.ainvoke(research_query)
            
            if isinstance(response, str):
                analysis_result = response
            else:
                analysis_result = response.content if hasattr(response, 'content') else str(response)
            
            logger.info(f"Dependency research completed: {len(all_tasks)} tasks analyzed")
            
            context.current_state = FlowState.COMPLETED
            
            return {
                "type": "execution_completed",
                "message": f"✅ **Dependency Analysis Completed**\n\nAnalyzed {len(all_tasks)} tasks:\n\n{analysis_result}",
                "state": "complete",
                "data": {
                    "tasks_analyzed": len(all_tasks),
                    "analysis": analysis_result
                }
            }
        
        except Exception as e:
            logger.error(f"Dependency research failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "type": "error",
                "message": f"Failed to analyze dependencies: {str(e)}",
                "state": context.current_state.value
            }
    
    async def _handle_update_task(
        self,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Handle UPDATE_TASK intent - Update a task"""
        logger.info("Handling UPDATE_TASK intent")
        
        try:
            task_id = context.gathered_data.get("task_id")
            task_title = context.gathered_data.get("task_title")
            
            # Extract update fields
            update_fields = {}
            if "new_title" in context.gathered_data:
                update_fields["title"] = context.gathered_data["new_title"]
            if "new_status" in context.gathered_data:
                update_fields["status"] = context.gathered_data["new_status"]
            if "new_priority" in context.gathered_data:
                update_fields["priority"] = context.gathered_data["new_priority"]
            if "new_estimated_hours" in context.gathered_data:
                update_fields["estimated_hours"] = context.gathered_data["new_estimated_hours"]
            if "new_description" in context.gathered_data:
                update_fields["description"] = context.gathered_data["new_description"]
            
            # Special case: bulk update for "delete all ETAs"
            # Check if we need to bulk update without task_id
            if not task_id and not task_title and "new_estimated_hours" in context.gathered_data:
                # Check if this is a deletion request (ETA set to 0 or None)
                eta_value = context.gathered_data["new_estimated_hours"]
                if eta_value == 0 or eta_value is None:
                    # Bulk update all user tasks
                    return await self._handle_bulk_eta_deletion(context)
            
            if not task_id and not task_title:
                return {
                    "type": "error",
                    "message": "Task ID or title is required to update a task. Please specify which task.",
                    "state": context.current_state.value
                }
            
            if not update_fields:
                return {
                    "type": "error",
                    "message": "No update fields provided. Please specify what to update (status, priority, title, etc.).",
                    "state": context.current_state.value
                }
            
            # Use PM provider - require task_id (no title lookup support)
            if task_id:
                task = await self.pm_provider.get_task(task_id)
                if not task:
                    return {
                        "type": "error",
                        "message": f"Task not found. Please check the task ID.",
                        "state": context.current_state.value
                    }
                
                updated_task = await self.pm_provider.update_task(task_id, update_fields)
                task_title_result = updated_task.title if hasattr(updated_task, 'title') else task_title
            else:
                # Try title lookup by searching tasks
                logger.info(f"Attempting to find task by title: {task_title}")
                all_tasks = await self.pm_provider.list_tasks()
                
                # Try exact match first
                matching_tasks = [t for t in all_tasks if t.title.lower() == task_title.lower()]
                if len(matching_tasks) == 0:
                    return {
                        "type": "error",
                        "message": f"Task '{task_title}' not found. Please specify the exact task title or use task ID.",
                        "state": context.current_state.value
                    }
                elif len(matching_tasks) > 1:
                    return {
                        "type": "error",
                        "message": f"Multiple tasks found with title '{task_title}'. Please specify task ID instead.",
                        "state": context.current_state.value
                    }
                else:
                    found_task = matching_tasks[0]
                    task_id = str(found_task.id)
                    logger.info(f"Found task '{task_title}' with ID: {task_id}")
                
                updated_task = await self.pm_provider.update_task(task_id, update_fields)
                task_title_result = updated_task.title if hasattr(updated_task, 'title') else task_title
            
            context.current_state = FlowState.COMPLETED
            
            # Format success message
            updates = ", ".join([f"{k.replace('_', ' ').title()}: {v}" for k, v in update_fields.items()])
            message = f"✅ Task **{task_title_result}** updated successfully!\n\n**Changes:** {updates}"
            
            return {
                "type": "execution_completed",
                "message": message,
                "state": context.current_state.value,
                "data": {
                    "task_id": str(getattr(updated_task, 'id', task_id)),
                    "task_title": task_title_result,
                    "updates": update_fields
                }
            }
        
        except Exception as e:
            logger.error(f"Update task failed: {e}")
            return {
                "type": "error",
                "message": f"Failed to update task: {str(e)}",
                "state": context.current_state.value
            }
    
    async def _handle_bulk_eta_deletion(
        self,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Handle bulk ETA deletion for all user tasks"""
        logger.info("Handling bulk ETA deletion")
        
        try:
            # Get current user's tasks
            current_user = await self.pm_provider.get_current_user()
            if not current_user:
                return {
                    "type": "error",
                    "message": "Cannot determine current user for bulk ETA deletion.",
                    "state": context.current_state.value
                }
            
            # List all user's tasks
            all_tasks = await self.pm_provider.list_tasks(assignee_id=str(current_user.id))
            
            # Filter tasks with ETA
            tasks_with_eta = [
                task for task in all_tasks
                if task.estimated_hours and task.estimated_hours > 0
            ]
            
            if not tasks_with_eta:
                context.current_state = FlowState.COMPLETED
                return {
                    "type": "execution_completed",
                    "message": "✅ All your tasks already have no ETA!",
                    "state": "complete"
                }
            
            # Update all tasks with ETA = 0
            updated_count = 0
            failed_count = 0
            for task in tasks_with_eta:
                try:
                    await self.pm_provider.update_task(str(task.id), {"estimated_hours": 0})
                    updated_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete ETA for task {task.id}: {e}")
                    failed_count += 1
            
            context.current_state = FlowState.COMPLETED
            
            message_parts = [
                f"✅ **Bulk ETA Deletion Completed**\n",
                f"Found {len(tasks_with_eta)} tasks with ETA\n",
                f"Successfully deleted ETA from {updated_count} tasks\n"
            ]
            
            if failed_count > 0:
                message_parts.append(f"Failed to update {failed_count} tasks\n")
            
            if updated_count > 0:
                message_parts.append("\n**Updated Tasks:**\n")
                for task in tasks_with_eta[:10]:  # Show first 10
                    message_parts.append(f"- {task.title}\n")
            
            if len(tasks_with_eta) > 10:
                message_parts.append(f"\n_... and {len(tasks_with_eta) - 10} more tasks_")
            
            return {
                "type": "execution_completed",
                "message": "".join(message_parts),
                "state": "complete",
                "data": {
                    "total_tasks": len(tasks_with_eta),
                    "updated_count": updated_count,
                    "failed_count": failed_count
                }
            }
        
        except Exception as e:
            logger.error(f"Bulk ETA deletion failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "type": "error",
                "message": f"Failed to delete ETAs: {str(e)}",
                "state": context.current_state.value
            }
    
    async def _handle_update_sprint(
        self,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """Handle UPDATE_SPRINT intent - Update a sprint"""
        logger.info("Handling UPDATE_SPRINT intent")
        
        try:
            sprint_id = context.gathered_data.get("sprint_id")
            sprint_name = context.gathered_data.get("sprint_name")
            
            if not sprint_id and not sprint_name:
                return {
                    "type": "error",
                    "message": "Sprint ID or name is required to update a sprint. Please specify which sprint.",
                    "state": context.current_state.value
                }
            
            # Extract update fields
            update_fields = {}
            if "new_status" in context.gathered_data:
                update_fields["status"] = context.gathered_data["new_status"]
            if "new_name" in context.gathered_data:
                update_fields["name"] = context.gathered_data["new_name"]
            if "new_capacity_hours" in context.gathered_data:
                update_fields["capacity_hours"] = context.gathered_data["new_capacity_hours"]
            if "new_start_date" in context.gathered_data:
                from datetime import datetime
                try:
                    update_fields["start_date"] = datetime.strptime(context.gathered_data["new_start_date"], "%Y-%m-%d").date()
                except ValueError:
                    return {
                        "type": "error",
                        "message": "Invalid start date format. Please use YYYY-MM-DD.",
                        "state": context.current_state.value
                    }
            if "new_end_date" in context.gathered_data:
                from datetime import datetime
                try:
                    update_fields["end_date"] = datetime.strptime(context.gathered_data["new_end_date"], "%Y-%m-%d").date()
                except ValueError:
                    return {
                        "type": "error",
                        "message": "Invalid end date format. Please use YYYY-MM-DD.",
                        "state": context.current_state.value
                    }
            
            if not update_fields:
                return {
                    "type": "error",
                    "message": "No update fields provided. Please specify what to update (status, name, capacity, etc.).",
                    "state": context.current_state.value
                }
            
            # Use PM provider - require sprint_id (no name lookup support)
            if sprint_id:
                sprint = await self.pm_provider.get_sprint(sprint_id)
                if not sprint:
                    return {
                        "type": "error",
                        "message": f"Sprint not found. Please check the sprint ID.",
                        "state": context.current_state.value
                    }
                
                updated_sprint = await self.pm_provider.update_sprint(sprint_id, update_fields)
                sprint_name_result = updated_sprint.name if hasattr(updated_sprint, 'name') else sprint_name
            else:
                # Name lookup not supported with PM providers
                return {
                    "type": "error",
                    "message": f"Please specify sprint ID to update. Name lookup is not supported.",
                    "state": context.current_state.value
                }
            
            context.current_state = FlowState.COMPLETED
            
            # Format success message
            updates = ", ".join([f"{k.replace('_', ' ').title()}: {v}" for k, v in update_fields.items()])
            message = f"✅ Sprint **{sprint_name_result}** updated successfully!\n\n**Changes:** {updates}"
            
            return {
                "type": "execution_completed",
                "message": message,
                "state": context.current_state.value,
                "data": {
                    "sprint_id": str(getattr(updated_sprint, 'id', sprint_id)),
                    "sprint_name": sprint_name_result,
                    "updates": update_fields
                }
            }
        
        except Exception as e:
            logger.error(f"Update sprint failed: {e}")
            return {
                "type": "error",
                "message": f"Failed to update sprint: {str(e)}",
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
    
    def _extract_key_facts(self, context: ConversationContext) -> str:
        """
        Extract key facts from gathered_data to provide context to LLM
        
        Args:
            context: Current conversation context
            
        Returns:
            Formatted string of key facts
        """
        facts = []
        
        # Active contexts
        if context.gathered_data.get("active_project_id"):
            project_name = context.gathered_data.get("active_project_name", "Unknown")
            facts.append(f"- Active Project: {project_name} (ID: {context.gathered_data['active_project_id']})")
        
        if context.gathered_data.get("active_sprint_id"):
            sprint_name = context.gathered_data.get("active_sprint_name", "Unknown")
            facts.append(f"- Active Sprint: {sprint_name} (ID: {context.gathered_data['active_sprint_id']})")
        
        if context.gathered_data.get("active_task_id"):
            task_title = context.gathered_data.get("active_task_title", "Unknown")
            facts.append(f"- Active Task: {task_title} (ID: {context.gathered_data['active_task_id']})")
        
        # Project context (from data extraction)
        if context.gathered_data.get("project_name"):
            facts.append(f"- Project Context: {context.gathered_data['project_name']}")
        
        # Recent actions (from pm_plan if exists)
        if context.gathered_data.get("_pm_plan"):
            pm_plan = context.gathered_data['_pm_plan']
            if isinstance(pm_plan, dict) and pm_plan.get("overall_thought"):
                facts.append(f"- Recent Plan: {pm_plan['overall_thought'][:100]}...")
        
        # User preferences/settings (if any)
        if context.gathered_data.get("filter_week"):
            facts.append("- Filter: Current week")
        
        if context.gathered_data.get("period"):
            facts.append(f"- Time Period: {context.gathered_data['period']}")
        
        # Research context
        if context.gathered_data.get("research_already_done"):
            facts.append("- Research: Already completed in this session")
        
        if not facts:
            return ""
        
        return "\n".join(facts)
    
    def _select_relevant_messages(
        self,
        conversation_history: List[Dict[str, str]],
        context: ConversationContext
    ) -> List[Dict[str, str]]:
        """
        Select most relevant messages using semantic importance scoring
        
        Prioritizes:
        - Recent messages (higher score)
        - Context switches (switch project/task/sprint)
        - Important actions (create WBS, list tasks)
        - Messages with extracted data
        
        Args:
            conversation_history: Full conversation history
            context: Current conversation context
            
        Returns:
            List of most relevant messages (sorted by importance)
        """
        if not conversation_history:
            return []
        
        # Score each message for importance
        scored_messages = []
        for i, msg in enumerate(conversation_history):
            score = self._score_message_importance(msg, context, i)
            scored_messages.append((score, msg))
        
        # Sort by score (descending) and take top messages
        scored_messages.sort(reverse=True, key=lambda x: x[0])
        
        # Take top 8 messages (4 user + 4 assistant pairs) to balance context and token usage
        max_messages = 8
        top_messages = [msg for _, msg in scored_messages[:max_messages]]
        
        # Also include recent messages (last 2) to ensure continuity
        recent_messages = conversation_history[-2:] if len(conversation_history) >= 2 else conversation_history
        
        # Combine and deduplicate while preserving order
        combined = []
        seen = set()
        for msg in top_messages + recent_messages:
            msg_id = id(msg)  # Use object id as hash since messages are dicts
            if msg_id not in seen:
                combined.append(msg)
                seen.add(msg_id)
        
        logger.info(f"Selected {len(combined)}/{len(conversation_history)} messages for context")
        return combined
    
    def _score_message_importance(
        self,
        msg: Dict[str, str],
        context: ConversationContext,
        index: int
    ) -> float:
        """
        Score message importance based on semantic content and recency
        
        Args:
            msg: Message to score
            context: Current conversation context
            index: Message index in history
            
        Returns:
            Importance score (higher = more important)
        """
        score = 0.0
        content = msg.get("content", "").lower()
        role = msg.get("role", "")
        
        # Recency boost (more recent = higher score)
        total_messages = len(context.conversation_history)
        if total_messages > 0:
            recency_factor = (total_messages - index) / total_messages
            score += recency_factor * 5
        
        # High importance keywords (context switches and important actions)
        high_importance_keywords = [
            "switch", "change to", "activate", "create wbs", "plan sprint",
            "clean all", "delete all", "update task", "update sprint"
        ]
        for keyword in high_importance_keywords:
            if keyword in content:
                score += 20
                break
        
        # Medium importance keywords (listings and queries)
        medium_importance_keywords = [
            "list", "show", "display", "get", "fetch", "retrieve",
            "assign", "eta", "estimated time", "my tasks", "my workload"
        ]
        for keyword in medium_importance_keywords:
            if keyword in content:
                score += 10
                break
        
        # Assistant messages with structured content (plan execution results)
        if role == "assistant":
            if "✅" in msg.get("content", "") or "❌" in msg.get("content", ""):
                score += 8
            if "steps" in content or "completed" in content:
                score += 5
        
        # Messages that triggered context updates
        if any(keyword in content for keyword in ["successful", "created", "updated", "switched"]):
            score += 7
        
        # Boost user messages slightly (they drive the conversation)
        if role == "user":
            score += 3
        
        return score


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
            IntentType.UPDATE_TASK: [
                "update task", "modify task", "change task", "edit task",
                "mark task", "complete task", "finish task"
            ],
            IntentType.UPDATE_SPRINT: [
                "update sprint", "modify sprint", "change sprint", "edit sprint"
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
                "update_task": "User wants to update or modify a task (status, priority, title, etc.)",
                "update_sprint": "User wants to update or modify a sprint (status, name, capacity, etc.)",
                "get_status": "User wants to check project status or progress",
                "get_project_status": "User wants to get project status and summary",
                "list_tasks": "User wants to list or show tasks for a project",
                "list_sprints": "User wants to list or show sprints for a project",
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
            
            # If LLM didn't return a valid intent, return UNKNOWN instead of keyword fallback
            logger.warning(f"LLM returned unknown intent: {intent_str}, returning UNKNOWN")
            return IntentType.UNKNOWN
            
        except Exception as e:
            logger.error(f"LLM-based intent classification failed: {e}, returning UNKNOWN")
            return IntentType.UNKNOWN
    
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
        
        gathered_data = gathered_data or {}
        
        if not self.llm:
            return gathered_data
        
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
            
            IntentType.UPDATE_TASK: """- task_id: UUID of the task (preferred)
- task_title: Title of the task to find
- new_title: New title for the task
- new_status: New status ("todo", "in_progress", "completed", "blocked")
- new_priority: New priority ("low", "medium", "high", "urgent")
- new_estimated_hours: New estimated hours (number, use 0 or null to delete/clear ETA)
- new_description: New description for the task""",
            
            IntentType.UPDATE_SPRINT: """- sprint_id: UUID of the sprint (preferred)
- sprint_name: Name of the sprint to find
- new_status: New status ("planned", "active", "completed", "blocked")
- new_name: New name for the sprint
- new_capacity_hours: New capacity in hours (number)
- new_start_date: New start date (format: YYYY-MM-DD)
- new_end_date: New end date (format: YYYY-MM-DD)""",
            
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
- focus_areas: Areas to focus on""",
            
            IntentType.LIST_MY_TASKS: """- filter_week: Boolean indicating if user wants tasks filtered by current week
- filter_date: Object with "start" and "end" dates in YYYY-MM-DD format
- period: Text description of time period (e.g., "this week", "next month", "today")"""
        }
        
        return descriptions.get(intent, "- No specific fields defined")
    
    # ==================== PM Provider Helper Methods ====================
    
    def _db_project_to_pm(self, project) -> 'PMProject':
        """Convert internal Project model to PMProject"""
        from src.pm_providers.models import PMProject
        from datetime import date, datetime
        
        return PMProject(
            id=str(project.id) if hasattr(project, 'id') else None,
            name=project.name,
            description=project.description,
            status=project.status if hasattr(project, 'status') else None,
            created_at=project.created_at if hasattr(project, 'created_at') else None,
            updated_at=project.updated_at if hasattr(project, 'updated_at') else None
        )
    
    def _db_task_to_pm(self, task) -> 'PMTask':
        """Convert internal Task model to PMTask"""
        from src.pm_providers.models import PMTask
        
        return PMTask(
            id=str(task.id) if hasattr(task, 'id') else None,
            title=task.title,
            description=task.description,
            status=task.status,
            priority=task.priority,
            project_id=str(task.project_id) if hasattr(task, 'project_id') else None,
            estimated_hours=task.estimated_hours,
            due_date=task.due_date if hasattr(task, 'due_date') else None,
            created_at=task.created_at if hasattr(task, 'created_at') else None,
            updated_at=task.updated_at if hasattr(task, 'updated_at') else None
        )
    
    def _pm_project_to_db(self, pm_project: 'PMProject'):
        """Convert PMProject to internal Project model"""
        from database.orm_models import Project
        from datetime import datetime
        
        return Project(
            name=pm_project.name,
            description=pm_project.description or "",
            status=pm_project.status,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def _pm_task_to_db(self, pm_task: 'PMTask', project_id=None):
        """Convert PMTask to internal Task model"""
        from database.orm_models import Task
        from uuid import UUID
        
        return Task(
            project_id=UUID(project_id) if project_id else None,
            title=pm_task.title,
            description=pm_task.description,
            status=pm_task.status or "todo",
            priority=pm_task.priority or "medium",
            estimated_hours=pm_task.estimated_hours
        )
