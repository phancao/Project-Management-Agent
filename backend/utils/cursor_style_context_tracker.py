# Cursor-Style Context Optimization
# Tracks cumulative context usage across all tools/agents and auto-optimizes when reaching 100%

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from langchain_core.messages import BaseMessage
import time

logger = logging.getLogger(__name__)


@dataclass
class ContextAllocation:
    """Represents a context allocation for a tool/agent."""
    name: str
    percentage: float  # 0.0 to 1.0 (e.g., 0.35 = 35%)
    allocated_tokens: int
    used_tokens: int = 0
    last_used: float = field(default_factory=time.time)
    
    @property
    def usage_percentage(self) -> float:
        """Calculate usage as percentage of allocation."""
        if self.allocated_tokens == 0:
            return 0.0
        return self.used_tokens / self.allocated_tokens
    
    @property
    def remaining_tokens(self) -> int:
        """Calculate remaining tokens in allocation."""
        return max(0, self.allocated_tokens - self.used_tokens)


class CursorStyleContextTracker:
    """
    Cursor-style context tracker that:
    1. Allocates context to each tool/agent as a percentage
    2. Tracks cumulative usage across all tools
    3. Auto-optimizes when total reaches 100%
    """
    
    def __init__(self, total_context_limit: int):
        """
        Initialize the context tracker.
        
        Args:
            total_context_limit: Total context window size (e.g., 16385, 128000)
        """
        self.total_limit = total_context_limit
        self.allocations: Dict[str, ContextAllocation] = {}
        self.total_used = 0
        self.optimization_threshold = 0.90  # Auto-optimize at 90% usage
        
        logger.info(
            f"[CURSOR-CONTEXT] Initialized tracker - "
            f"total_limit={total_context_limit:,} tokens, "
            f"optimization_threshold={self.optimization_threshold:.0%}"
        )
    
    def allocate(
        self, 
        name: str, 
        percentage: float,
        description: str = ""
    ) -> ContextAllocation:
        """
        Allocate context to a tool/agent as a percentage of total.
        
        Args:
            name: Name of tool/agent (e.g., 'react_agent', 'list_projects')
            percentage: Percentage of total context (0.0 to 1.0)
            description: Optional description
            
        Returns:
            ContextAllocation object
            
        Example:
            tracker.allocate('react_agent', 0.35)  # 35% of total
        """
        allocated_tokens = int(self.total_limit * percentage)
        
        allocation = ContextAllocation(
            name=name,
            percentage=percentage,
            allocated_tokens=allocated_tokens
        )
        
        self.allocations[name] = allocation
        
        logger.info(
            f"[CURSOR-CONTEXT] Allocated {percentage:.0%} ({allocated_tokens:,} tokens) "
            f"to '{name}' {description}"
        )
        
        return allocation
    
    def record_usage(
        self, 
        name: str, 
        tokens_used: int,
        messages: Optional[List[BaseMessage]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Record context usage for a tool/agent.
        
        Args:
            name: Name of tool/agent
            tokens_used: Number of tokens used
            messages: Optional messages for optimization
            
        Returns:
            Tuple of (needs_optimization, optimization_reason)
        """
        if name not in self.allocations:
            logger.warning(f"[CURSOR-CONTEXT] No allocation for '{name}', skipping tracking")
            return False, None
        
        allocation = self.allocations[name]
        allocation.used_tokens += tokens_used
        allocation.last_used = time.time()
        self.total_used += tokens_used
        
        # Check if this allocation is over budget
        allocation_over = allocation.used_tokens > allocation.allocated_tokens
        
        # Check if total usage is approaching limit
        total_usage_percentage = self.total_used / self.total_limit
        total_over = total_usage_percentage >= self.optimization_threshold
        
        
        # Determine if optimization is needed
        if total_over:
            return True, f"Total context usage ({total_usage_percentage:.0%}) exceeds threshold ({self.optimization_threshold:.0%})"
        elif allocation_over:
            return True, f"Allocation '{name}' ({allocation.usage_percentage:.0%}) exceeds budget"
        
        return False, None
    
    def get_available_tokens(self, name: str) -> int:
        """Get remaining available tokens for an allocation."""
        if name not in self.allocations:
            return 0
        return self.allocations[name].remaining_tokens
    
    def get_total_usage_percentage(self) -> float:
        """Get total usage as percentage of total limit."""
        return self.total_used / self.total_limit
    
    def should_optimize(self) -> Tuple[bool, str]:
        """
        Check if optimization is needed.
        
        Returns:
            Tuple of (should_optimize, reason)
        """
        total_usage = self.get_total_usage_percentage()
        
        if total_usage >= 1.0:
            return True, f"Context usage at 100% ({self.total_used:,}/{self.total_limit:,} tokens)"
        elif total_usage >= self.optimization_threshold:
            return True, f"Context usage at {total_usage:.0%} (threshold: {self.optimization_threshold:.0%})"
        
        # Check individual allocations
        for name, allocation in self.allocations.items():
            if allocation.usage_percentage >= 1.0:
                return True, f"Allocation '{name}' at 100% ({allocation.used_tokens:,}/{allocation.allocated_tokens:,} tokens)"
            elif allocation.usage_percentage >= 0.95:
                return True, f"Allocation '{name}' at {allocation.usage_percentage:.0%} (approaching limit)"
        
        return False, ""
    
    def optimize(self, context_manager) -> Dict[str, any]:
        """
        Perform optimization by compressing context.
        
        Args:
            context_manager: ContextManager instance for compression
            
        Returns:
            Optimization metadata
        """
        logger.info(
            f"[CURSOR-CONTEXT] 🔄 Auto-optimizing - "
            f"Total usage: {self.get_total_usage_percentage():.0%} "
            f"({self.total_used:,}/{self.total_limit:,} tokens)"
        )
        
        # Reset usage counters (compression frees up space)
        old_total = self.total_used
        for allocation in self.allocations.values():
            # Reduce usage by compression ratio (estimate 50% reduction)
            allocation.used_tokens = int(allocation.used_tokens * 0.5)
        
        self.total_used = sum(a.used_tokens for a in self.allocations.values())
        
        reduction = old_total - self.total_used
        logger.info(
            f"[CURSOR-CONTEXT] ✅ Optimization complete - "
            f"Freed {reduction:,} tokens "
            f"({old_total:,} → {self.total_used:,}, "
            f"{self.get_total_usage_percentage():.0%} usage)"
        )
        
        return {
            "optimized": True,
            "old_total": old_total,
            "new_total": self.total_used,
            "freed_tokens": reduction,
            "usage_percentage": self.get_total_usage_percentage()
        }
    
    def reset(self):
        """Reset all usage counters (e.g., at start of new request)."""
        old_total = self.total_used
        for allocation in self.allocations.values():
            allocation.used_tokens = 0
        self.total_used = 0
        
        logger.info(
            f"[CURSOR-CONTEXT] Reset tracker - "
            f"Cleared {old_total:,} tokens of usage"
        )
    
    def get_status(self) -> Dict[str, any]:
        """Get current status of all allocations."""
        return {
            "total_limit": self.total_limit,
            "total_used": self.total_used,
            "total_usage_percentage": self.get_total_usage_percentage(),
            "allocations": {
                name: {
                    "percentage": alloc.percentage,
                    "allocated": alloc.allocated_tokens,
                    "used": alloc.used_tokens,
                    "remaining": alloc.remaining_tokens,
                    "usage_percentage": alloc.usage_percentage
                }
                for name, alloc in self.allocations.items()
            }
        }


# Global tracker instance (per-request, created in nodes)
_global_tracker: Optional[CursorStyleContextTracker] = None


def get_global_tracker() -> Optional[CursorStyleContextTracker]:
    """Get the global context tracker."""
    return _global_tracker


def set_global_tracker(tracker: CursorStyleContextTracker):
    """Set the global context tracker."""
    global _global_tracker
    _global_tracker = tracker
    logger.info(f"[CURSOR-CONTEXT] Global tracker set: {tracker.total_limit:,} tokens")


def create_tracker_for_request(total_context_limit: int) -> CursorStyleContextTracker:
    """
    Create a new tracker for a request.
    
    This should be called at the start of each request to track context usage
    across all agents/tools in that request.
    """
    tracker = CursorStyleContextTracker(total_context_limit)
    set_global_tracker(tracker)
    return tracker


