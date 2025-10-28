"""
Conversation Flow Manager for Project Management Agent

This module handles adaptive conversation flows, intent classification,
and progressive data gathering for project management tasks.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

class IntentType(Enum):
    """Types of user intents"""
    CREATE_PROJECT = "create_project"
    PLAN_TASKS = "plan_tasks"
    RESEARCH_TOPIC = "research_topic"
    UPDATE_PROJECT = "update_project"
    GET_STATUS = "get_status"
    HELP = "help"
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
    
    def __init__(self):
        self.contexts: Dict[str, ConversationContext] = {}
        self.intent_classifier = IntentClassifier()
        self.question_generator = QuestionGenerator()
        self.data_validator = DataValidator()
        
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
            context.intent = await self.intent_classifier.classify(message)
            context.current_state = FlowState.CONTEXT_GATHERING
            
        # Check if we have enough context
        if context.current_state == FlowState.CONTEXT_GATHERING:
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
        # TODO: Integrate with DeerFlow
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
        # TODO: Execute planned actions
        context.current_state = FlowState.COMPLETED
        
        return {
            "type": "execution_completed",
            "message": "Project management tasks completed!",
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

class IntentClassifier:
    """Classifies user intent from messages"""
    
    def __init__(self):
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
                "edit project", "update my project", "modify my project",
                "change my project", "edit my project"
            ],
            IntentType.GET_STATUS: [
                "status", "progress", "how is", "project status",
                "current status"
            ],
            IntentType.HELP: [
                "help", "what can you do", "how to", "guide"
            ]
        }
    
    async def classify(self, message: str) -> IntentType:
        """Classify user intent from message"""
        import re
        message_lower = message.lower()
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                # Use regex to match pattern with optional words in between
                # e.g., "update project" matches "update my project"
                regex_pattern = pattern.replace(" ", r"\s+\w*\s*")
                if re.search(regex_pattern, message_lower):
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
