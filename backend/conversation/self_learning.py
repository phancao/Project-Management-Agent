"""
Self-Learning System for Intent Classification

This module implements a self-learning system that improves intent classification
based on user feedback and historical data.
"""

import logging
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime

logger = logging.getLogger(__name__)


class SelfLearningSystem:
    """Self-learning system for intent classification"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    def record_classification(
        self,
        session_id: str,
        message: str,
        classified_intent: str,
        confidence_score: float = 0.0,
        conversation_history: List[Dict[str, Any]] = None
    ) -> str:
        """
        Record an intent classification for learning
        
        Returns:
            classification_id: ID of the recorded classification
        """
        try:
            from database.orm_models import IntentClassification
            
            classification = IntentClassification(
                session_id=None,  # Set to NULL for now - session_id string doesn't map to UUID id
                message=message,
                classified_intent=classified_intent,
                confidence_score=confidence_score,
                conversation_history=conversation_history or []
            )
            
            self.db_session.add(classification)
            self.db_session.commit()
            self.db_session.refresh(classification)
            
            logger.info(f"Recorded classification: {classified_intent} for message: {message[:50]}")
            return str(classification.id)
            
        except Exception as e:
            logger.error(f"Failed to record classification: {e}")
            self.db_session.rollback()
            return None
    
    def record_feedback(
        self,
        classification_id: str,
        feedback_type: str,
        was_correct: bool = None,
        user_corrected_intent: str = None,
        original_message: str = None,
        suggested_intent: str = None,
        user_comment: str = None
    ):
        """Record user feedback on classification"""
        try:
            from database.orm_models import IntentClassification, IntentFeedback
            
            # Get the classification
            classification = self.db_session.query(IntentClassification).filter_by(
                id=classification_id
            ).first()
            
            if not classification:
                logger.error(f"Classification not found: {classification_id}")
                return
            
            # Update classification with feedback
            if was_correct is not None:
                classification.was_correct = was_correct
                if user_corrected_intent:
                    classification.user_corrected_intent = user_corrected_intent
            
            # Create feedback record
            feedback = IntentFeedback(
                classification_id=classification_id,
                feedback_type=feedback_type,
                original_message=original_message,
                suggested_intent=suggested_intent or user_corrected_intent,
                user_comment=user_comment
            )
            
            self.db_session.add(feedback)
            
            # Update metrics
            self._update_metrics(classified_intent=classification.classified_intent, 
                               was_correct=was_correct)
            
            # Learn from feedback
            if feedback_type == "correction" and user_corrected_intent:
                self._learn_pattern(
                    message=classification.message,
                    correct_intent=user_corrected_intent,
                    wrong_intent=classification.classified_intent
                )
            
            self.db_session.commit()
            logger.info(f"Recorded feedback for classification: {classification_id}")
            
        except Exception as e:
            logger.error(f"Failed to record feedback: {e}")
            self.db_session.rollback()
    
    def _update_metrics(self, classified_intent: str, was_correct: bool):
        """Update intent classification metrics"""
        try:
            from database.orm_models import IntentMetric
            
            metric = self.db_session.query(IntentMetric).filter_by(
                intent_type=classified_intent
            ).first()
            
            if not metric:
                metric = IntentMetric(intent_type=classified_intent)
                self.db_session.add(metric)
            
            metric.total_classifications += 1
            if was_correct:
                metric.correct_classifications += 1
            
            # Calculate success rate
            metric.success_rate = (
                metric.correct_classifications / metric.total_classifications
                if metric.total_classifications > 0 else 0.0
            )
            
            metric.last_updated = datetime.utcnow()
            self.db_session.commit()
            
        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")
            self.db_session.rollback()
    
    def _learn_pattern(
        self,
        message: str,
        correct_intent: str,
        wrong_intent: str
    ):
        """Learn new pattern from correction"""
        try:
            from database.orm_models import LearnedIntentPattern
            
            # Try to extract key phrases or patterns from the message
            # For now, simple approach: use the message itself as a pattern
            pattern = message.lower().strip()
            
            # Check if pattern already exists
            existing_pattern = self.db_session.query(LearnedIntentPattern).filter_by(
                intent_type=correct_intent,
                pattern_text=pattern
            ).first()
            
            if existing_pattern:
                # Increment success count
                existing_pattern.success_count += 1
                existing_pattern.last_used_at = datetime.utcnow()
                
                # Recalculate confidence
                total = existing_pattern.success_count + existing_pattern.failure_count
                existing_pattern.confidence = existing_pattern.success_count / total if total > 0 else 0
            else:
                # Create new pattern
                new_pattern = LearnedIntentPattern(
                    intent_type=correct_intent,
                    pattern_text=pattern,
                    success_count=1,
                    pattern_type="phrase"
                )
                self.db_session.add(new_pattern)
            
            # Also mark the wrong intent's patterns as having failed
            wrong_pattern = self.db_session.query(LearnedIntentPattern).filter_by(
                intent_type=wrong_intent,
                pattern_text=pattern
            ).first()
            
            if wrong_pattern:
                wrong_pattern.failure_count += 1
                # Recalculate confidence
                total = wrong_pattern.success_count + wrong_pattern.failure_count
                wrong_pattern.confidence = wrong_pattern.success_count / total if total > 0 else 0
                wrong_pattern.last_used_at = datetime.utcnow()
            
            self.db_session.commit()
            
        except Exception as e:
            logger.error(f"Failed to learn pattern: {e}")
            self.db_session.rollback()
    
    def get_learned_patterns(self, intent_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get learned patterns for an intent, sorted by confidence"""
        try:
            from database.orm_models import LearnedIntentPattern
            
            patterns = self.db_session.query(LearnedIntentPattern).filter_by(
                intent_type=intent_type
            ).order_by(
                LearnedIntentPattern.confidence.desc(),
                LearnedIntentPattern.success_count.desc()
            ).limit(limit).all()
            
            return [
                {
                    "pattern": p.pattern_text,
                    "confidence": p.confidence,
                    "success_count": p.success_count,
                    "failure_count": p.failure_count
                }
                for p in patterns
            ]
            
        except Exception as e:
            logger.error(f"Failed to get learned patterns: {e}")
            return []
    
    def get_intent_metrics(self) -> Dict[str, Any]:
        """Get overall intent classification metrics"""
        try:
            from database.orm_models import IntentMetric
            
            metrics = self.db_session.query(IntentMetric).all()
            
            return {
                "total_intents": len(metrics),
                "intents": [
                    {
                        "intent": m.intent_type,
                        "total": m.total_classifications,
                        "correct": m.correct_classifications,
                        "success_rate": m.success_rate,
                        "avg_confidence": m.average_confidence
                    }
                    for m in metrics
                ],
                "overall_success_rate": (
                    sum(m.success_rate for m in metrics) / len(metrics)
                    if metrics else 0.0
                )
            }
            
        except Exception as e:
            logger.error(f"Failed to get intent metrics: {e}")
            return {}
    
    def improve_classifier_prompt(self, base_prompt: str) -> str:
        """
        Enhance the classifier prompt based on learned patterns
        
        This adds context about successful patterns to the LLM prompt
        """
        try:
            # Get high-confidence learned patterns
            from database.orm_models import LearnedIntentPattern
            
            high_confidence_patterns = self.db_session.query(LearnedIntentPattern).filter(
                LearnedIntentPattern.confidence >= 0.8,
                LearnedIntentPattern.success_count >= 3
            ).all()
            
            if not high_confidence_patterns:
                return base_prompt
            
            # Group patterns by intent
            patterns_by_intent = {}
            for p in high_confidence_patterns:
                if p.intent_type not in patterns_by_intent:
                    patterns_by_intent[p.intent_type] = []
                patterns_by_intent[p.intent_type].append(p.pattern_text)
            
            # Build additional context
            context_lines = ["\nLearned successful patterns:"]
            for intent, patterns in patterns_by_intent.items():
                context_lines.append(f"\n{intent}:")
                for pattern in patterns[:3]:  # Top 3 patterns per intent
                    context_lines.append(f"  - \"{pattern}\"")
            
            enhanced_prompt = base_prompt + "\n" + "\n".join(context_lines)
            return enhanced_prompt
            
        except Exception as e:
            logger.error(f"Failed to improve prompt: {e}")
            return base_prompt

