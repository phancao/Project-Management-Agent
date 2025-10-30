"""
Conversation Flow Manager for Project Management Agent

This module handles adaptive conversation flows, intent classification,
and progressive data gathering for project management tasks.
"""

import logging
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
            return await self._handle_research_phase(context)
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
        
        # For RESEARCH_TOPIC intent, use DeerFlow directly
        if context.intent == IntentType.RESEARCH_TOPIC and self.run_deerflow_workflow:
            topic = context.gathered_data.get("topic", "")
            
            if not topic:
                return {
                    "type": "error",
                    "message": "No research topic provided. Please specify what you'd like to research.",
                    "state": context.current_state.value
                }
            
            try:
                # Create initial messages for DeerFlow
                messages = [{"role": "user", "content": f"Research: {topic}"}]
                
                # Run DeerFlow workflow
                async for event in self.run_deerflow_workflow(
                    messages=messages,
                    thread_id=context.session_id,
                    max_plan_iterations=1,
                    max_step_num=3,
                    max_search_results=3,
                    auto_accepted_plan=True
                ):
                    # Stream events back (can be captured by caller)
                    logger.debug(f"DeerFlow event: {event}")
                
                # After research completes, move to completed state
                context.current_state = FlowState.COMPLETED
                
                return {
                    "type": "research_completed",
                    "message": f"Research on '{topic}' has been completed using DeerFlow.",
                    "state": context.current_state.value,
                    "data": {"topic": topic}
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
            
            IntentType.CREATE_WBS: """- project_id: ID of the project
- breakdown_levels: Number of levels in WBS
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
