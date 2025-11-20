"""
Smart Debug Log Configuration

Allows enabling/disabling debug logs per module before running.
This helps reduce noise in logs and focus on specific areas when debugging.

Usage:
    # Enable debug for specific modules
    from src.config.debug_config import DebugConfig
    debug_config = DebugConfig(
        deerflow=True,
        pm_provider=True,
        analytics=False
    )
    debug_config.apply()
    
    # Or via environment variables
    DEBUG_DEERFLOW=true DEBUG_PM_PROVIDER=true python server.py
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class DebugConfig:
    """
    Configuration for module-specific debug logging.
    
    Each module can be independently enabled/disabled for debug logging.
    """
    # Core modules
    deerflow: bool = False  # DeerFlow workflow, graph, agents
    pm_provider: bool = False  # PM providers, PM handler, PM MCP server
    analytics: bool = False  # Analytics service, adapters, calculators
    conversation: bool = False  # Conversation flow manager
    tools: bool = False  # All tools (search, crawl, retriever, etc.)
    rag: bool = False  # RAG retriever and builders
    crawler: bool = False  # Web crawler
    
    # Sub-modules (more granular control)
    pm_providers: bool = False  # Individual PM providers (JIRA, OpenProject, etc.)
    pm_mcp_server: bool = False  # PM MCP server specifically
    pm_handler: bool = False  # PM handler abstraction layer
    analytics_service: bool = False  # Analytics service
    analytics_adapters: bool = False  # Analytics adapters
    analytics_calculators: bool = False  # Analytics calculators
    
    # Agent-specific
    agents: bool = False  # Agent creation and execution
    graph: bool = False  # Graph nodes and execution
    workflow: bool = False  # Workflow orchestration
    
    # Tools-specific
    search_tools: bool = False  # Search tools (Tavily, etc.)
    pm_tools: bool = False  # PM tools
    analytics_tools: bool = False  # Analytics tools
    
    # MCP
    mcp: bool = False  # MCP client and server connections
    
    def __post_init__(self):
        """Apply parent module settings to sub-modules if not explicitly set."""
        # If parent is enabled, enable children unless explicitly disabled
        if self.pm_provider and not hasattr(self, '_pm_provider_set'):
            self.pm_providers = self.pm_providers or self.pm_provider
            self.pm_mcp_server = self.pm_mcp_server or self.pm_provider
            self.pm_handler = self.pm_handler or self.pm_provider
        
        if self.analytics and not hasattr(self, '_analytics_set'):
            self.analytics_service = self.analytics_service or self.analytics
            self.analytics_adapters = self.analytics_adapters or self.analytics
            self.analytics_calculators = self.analytics_calculators or self.analytics
        
        if self.tools and not hasattr(self, '_tools_set'):
            self.search_tools = self.search_tools or self.tools
            self.pm_tools = self.pm_tools or self.tools
            self.analytics_tools = self.analytics_tools or self.tools
    
    @classmethod
    def from_env(cls) -> "DebugConfig":
        """Create DebugConfig from environment variables.
        
        Environment variables:
            DEBUG_DEERFLOW=true
            DEBUG_PM_PROVIDER=true
            DEBUG_ANALYTICS=true
            DEBUG_CONVERSATION=true
            DEBUG_TOOLS=true
            DEBUG_RAG=true
            DEBUG_CRAWLER=true
            DEBUG_PM_PROVIDERS=true
            DEBUG_PM_MCP_SERVER=true
            DEBUG_PM_HANDLER=true
            DEBUG_ANALYTICS_SERVICE=true
            DEBUG_ANALYTICS_ADAPTERS=true
            DEBUG_ANALYTICS_CALCULATORS=true
            DEBUG_AGENTS=true
            DEBUG_GRAPH=true
            DEBUG_WORKFLOW=true
            DEBUG_SEARCH_TOOLS=true
            DEBUG_PM_TOOLS=true
            DEBUG_ANALYTICS_TOOLS=true
            DEBUG_MCP=true
        """
        def get_bool_env(key: str, default: bool = False) -> bool:
            value = os.getenv(key, "").lower()
            return value in ("true", "1", "yes", "on")
        
        return cls(
            deerflow=get_bool_env("DEBUG_DEERFLOW"),
            pm_provider=get_bool_env("DEBUG_PM_PROVIDER"),
            analytics=get_bool_env("DEBUG_ANALYTICS"),
            conversation=get_bool_env("DEBUG_CONVERSATION"),
            tools=get_bool_env("DEBUG_TOOLS"),
            rag=get_bool_env("DEBUG_RAG"),
            crawler=get_bool_env("DEBUG_CRAWLER"),
            pm_providers=get_bool_env("DEBUG_PM_PROVIDERS"),
            pm_mcp_server=get_bool_env("DEBUG_PM_MCP_SERVER"),
            pm_handler=get_bool_env("DEBUG_PM_HANDLER"),
            analytics_service=get_bool_env("DEBUG_ANALYTICS_SERVICE"),
            analytics_adapters=get_bool_env("DEBUG_ANALYTICS_ADAPTERS"),
            analytics_calculators=get_bool_env("DEBUG_ANALYTICS_CALCULATORS"),
            agents=get_bool_env("DEBUG_AGENTS"),
            graph=get_bool_env("DEBUG_GRAPH"),
            workflow=get_bool_env("DEBUG_WORKFLOW"),
            search_tools=get_bool_env("DEBUG_SEARCH_TOOLS"),
            pm_tools=get_bool_env("DEBUG_PM_TOOLS"),
            analytics_tools=get_bool_env("DEBUG_ANALYTICS_TOOLS"),
            mcp=get_bool_env("DEBUG_MCP"),
        )
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, bool]) -> "DebugConfig":
        """Create DebugConfig from a dictionary."""
        return cls(**{k: v for k, v in config_dict.items() if hasattr(cls, k)})
    
    def apply(self) -> None:
        """Apply debug configuration to logging system."""
        # Module to logger name mapping
        module_loggers = {
            # Core modules
            "deerflow": ["src.workflow", "src.graph", "src.agents"],
            "pm_provider": ["src.pm_providers", "src.server.pm_handler", "src.mcp_servers.pm_server"],
            "analytics": ["src.analytics"],
            "conversation": ["src.conversation"],
            "tools": ["src.tools"],
            "rag": ["src.rag"],
            "crawler": ["src.crawler"],
            
            # Sub-modules
            "pm_providers": ["src.pm_providers"],
            "pm_mcp_server": ["src.mcp_servers.pm_server"],
            "pm_handler": ["src.server.pm_handler"],
            "analytics_service": ["src.analytics.service"],
            "analytics_adapters": ["src.analytics.adapters"],
            "analytics_calculators": ["src.analytics.calculators"],
            "agents": ["src.agents"],
            "graph": ["src.graph"],
            "workflow": ["src.workflow"],
            "search_tools": ["src.tools.search", "src.tools.tavily_search"],
            "pm_tools": ["src.tools.pm_tools", "src.tools.pm_mcp_tools"],
            "analytics_tools": ["src.tools.analytics_tools"],
            "mcp": ["src.server.mcp_utils", "src.mcp_servers"],
        }
        
        enabled_modules = []
        for module_name, logger_names in module_loggers.items():
            if getattr(self, module_name, False):
                enabled_modules.append(module_name)
                for logger_name in logger_names:
                    logging.getLogger(logger_name).setLevel(logging.DEBUG)
        
        if enabled_modules:
            logger.info(
                f"🔍 Debug logging enabled for modules: {', '.join(enabled_modules)}"
            )
        else:
            logger.debug("No debug modules enabled")
    
    def to_dict(self) -> Dict[str, bool]:
        """Convert to dictionary."""
        return {
            field.name: getattr(self, field.name)
            for field in self.__dataclass_fields__.values()
        }
    
    def __str__(self) -> str:
        """String representation."""
        enabled = [k for k, v in self.to_dict().items() if v]
        if enabled:
            return f"DebugConfig(enabled={', '.join(enabled)})"
        return "DebugConfig(no modules enabled)"


# Global debug config instance
_global_debug_config: Optional[DebugConfig] = None


def get_debug_config() -> DebugConfig:
    """Get the global debug configuration."""
    global _global_debug_config
    if _global_debug_config is None:
        _global_debug_config = DebugConfig.from_env()
    return _global_debug_config


def set_debug_config(config: DebugConfig) -> None:
    """Set the global debug configuration and apply it."""
    global _global_debug_config
    _global_debug_config = config
    config.apply()


def reset_debug_config() -> None:
    """Reset debug configuration to defaults."""
    global _global_debug_config
    _global_debug_config = DebugConfig()
    # Reset all module loggers to INFO
    for logger_name in [
        "src.workflow", "src.graph", "src.agents",
        "src.pm_providers", "src.server.pm_handler", "src.mcp_servers.pm_server",
        "src.analytics", "src.conversation", "src.tools", "src.rag", "src.crawler",
    ]:
        logging.getLogger(logger_name).setLevel(logging.INFO)

