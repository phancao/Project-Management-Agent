"""
Tool Registry Service

Simplifies tool registration with consistent interface.
"""

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Service for managing tool registration."""
    
    def __init__(self):
        """Initialize tool registry."""
        self._tool_names: List[str] = []
        self._tool_functions: Dict[str, Any] = {}
        self._registered_modules: List[str] = []
    
    def register_tool(
        self,
        tool_name: str,
        tool_func: Callable,
        module_name: Optional[str] = None
    ) -> None:
        """
        Register a tool function.
        
        Args:
            tool_name: Name of the tool
            tool_func: Tool function to register
            module_name: Optional module name for tracking
        """
        if tool_name in self._tool_functions:
            logger.warning(f"Tool '{tool_name}' already registered, overwriting")
        
        self._tool_names.append(tool_name)
        self._tool_functions[tool_name] = tool_func
        
        if module_name:
            if module_name not in self._registered_modules:
                self._registered_modules.append(module_name)
    
    def get_tool_function(self, tool_name: str) -> Optional[Callable]:
        """
        Get tool function by name.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool function if found, None otherwise
        """
        return self._tool_functions.get(tool_name)
    
    def list_tool_names(self) -> List[str]:
        """List all registered tool names."""
        return self._tool_names.copy()
    
    def get_tool_count(self) -> int:
        """Get total number of registered tools."""
        return len(self._tool_names)
    
    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool is registered."""
        return tool_name in self._tool_functions

