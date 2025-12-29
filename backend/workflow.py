# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import asyncio
import logging
import os

from shared.config.configuration import get_recursion_limit
from backend.graph import build_graph
from backend.graph.utils import build_clarified_topic_from_history

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Default level is INFO
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def enable_debug_logging():
    """Enable debug level logging for more detailed execution information."""
    logging.getLogger("src").setLevel(logging.DEBUG)


logger = logging.getLogger(__name__)

# Create the graph
graph = build_graph()


async def run_agent_workflow_async(
    user_input: str,
    debug: bool = False,
    max_plan_iterations: int = 1,
    max_step_num: int = 3,
    enable_background_investigation: bool = True,
    enable_clarification: bool | None = None,
    max_clarification_rounds: int | None = None,
    initial_state: dict | None = None,
):
    """Run the agent workflow asynchronously with the given user input.

    Args:
        user_input: The user's query or request
        debug: If True, enables debug level logging
        max_plan_iterations: Maximum number of plan iterations
        max_step_num: Maximum number of steps in a plan
        enable_background_investigation: If True, performs web search before planning to enhance context
        enable_clarification: If None, use default from State class (False); if True/False, override
        max_clarification_rounds: Maximum number of clarification rounds allowed
        initial_state: Initial state to use (for recursive calls during clarification)

    Returns:
        The final state after the workflow completes
    """
    if not user_input:
        raise ValueError("Input could not be empty")

    if debug:
        enable_debug_logging()

    logger.info(f"Starting async workflow with user input: {user_input}")

    # Use provided initial_state or create a new one
    if initial_state is None:
        initial_state = {
            # Runtime Variables
            "messages": [{"role": "user", "content": user_input}],
            "auto_accepted_plan": True,
            "enable_background_investigation": enable_background_investigation,
        }
        initial_state["research_topic"] = user_input
        initial_state["clarified_research_topic"] = user_input

        # Only set clarification parameter if explicitly provided
        # If None, State class default will be used (enable_clarification=False)
        if enable_clarification is not None:
            initial_state["enable_clarification"] = enable_clarification

        if max_clarification_rounds is not None:
            initial_state["max_clarification_rounds"] = max_clarification_rounds

    config = {
        "configurable": {
            "thread_id": "default",
            "max_plan_iterations": max_plan_iterations,
            "max_step_num": max_step_num,
            "mcp_settings": {
                "servers": {
                    "pm-server": {
                        "transport": "sse",
                        "url": "http://pm_mcp_server:8080/sse",
                        "headers": {
                            "X-MCP-API-Key": os.getenv("PM_MCP_API_KEY", "mcp_a9b43d595b627e1e094209dea14bcb32f98867649ae181d4836dde87e283ccc3")
                        },
                        "enabled_tools": None,  # Enable all available PM tools
                        "add_to_agents": ["pm_agent"],  # Only PM Agent should have PM tools
                    },
                    "mcp-github-trending": {
                        "transport": "stdio",
                        "command": "uvx",
                        "args": ["mcp-github-trending"],
                        "enabled_tools": ["get_github_trending_repositories"],
                        "add_to_agents": ["researcher"],
                    }
                }
            },
        },
        "recursion_limit": get_recursion_limit(default=100),
    }
    last_message_cnt = 0
    final_state = None
    async for s in graph.astream(
        input=initial_state, config=config, stream_mode="values"
    ):
        try:
            final_state = s
            if isinstance(s, dict) and "messages" in s:
                if len(s["messages"]) <= last_message_cnt:
                    continue
                last_message_cnt = len(s["messages"])
                message = s["messages"][-1]
                if isinstance(message, tuple):
                    print(message)
                else:
                    message.pretty_print()
            else:
                print(f"Output: {s}")
        except Exception as e:
            logger.error(f"Error processing stream output: {e}")
            print(f"Error processing output: {str(e)}")

    # Check if clarification is needed using centralized logic
    if final_state and isinstance(final_state, dict):
        from backend.graph.nodes import needs_clarification

        if needs_clarification(final_state):
            # Wait for user input
            print()
            clarification_rounds = final_state.get("clarification_rounds", 0)
            max_clarification_rounds = final_state.get("max_clarification_rounds", 3)
            user_response = input(
                f"Your response ({clarification_rounds}/{max_clarification_rounds}): "
            ).strip()

            if not user_response:
                logger.warning("Empty response, ending clarification")
                return final_state

            # Continue workflow with user response
            current_state = final_state.copy()
            current_state["messages"] = final_state["messages"] + [
                {"role": "user", "content": user_response}
            ]
            for key in (
                "clarification_history",
                "clarification_rounds",
                "clarified_research_topic",
                "research_topic",
                "locale",
                "enable_clarification",
                "max_clarification_rounds",
            ):
                if key in final_state:
                    current_state[key] = final_state[key]

            return await run_agent_workflow_async(
                user_input=user_response,
                max_plan_iterations=max_plan_iterations,
                max_step_num=max_step_num,
                enable_background_investigation=enable_background_investigation,
                enable_clarification=enable_clarification,
                max_clarification_rounds=max_clarification_rounds,
                initial_state=current_state,
            )

    logger.info("Async workflow completed successfully")

    return final_state


async def run_agent_workflow_stream(
    user_input: str,
    debug: bool = False,
    max_plan_iterations: int = 1,
    max_step_num: int = 3,
    enable_background_investigation: bool = True,
    enable_clarification: bool | None = None,
    max_clarification_rounds: int | None = None,
    initial_state: dict | None = None,
):
    """Run the agent workflow asynchronously and yield intermediate states.
    
    This is the streaming version of run_agent_workflow_async that yields
    intermediate states as they arrive, useful for showing progress in real-time.
    
    Args:
        user_input: The user's query or request
        debug: If True, enables debug level logging
        max_plan_iterations: Maximum number of plan iterations
        max_step_num: Maximum number of steps in a plan
        enable_background_investigation: If True, performs web search before planning to enhance context
        enable_clarification: If None, use default from State class (False); if True/False, override
        max_clarification_rounds: Maximum number of clarification rounds allowed
        initial_state: Initial state to use (for recursive calls during clarification)
    
    Yields:
        Intermediate states from the workflow as they complete
    """
    if not user_input:
        raise ValueError("Input could not be empty")

    if debug:
        enable_debug_logging()


    # Use provided initial_state or create a new one
    if initial_state is None:
        initial_state = {
            # Runtime Variables
            "messages": [{"role": "user", "content": user_input}],
            "auto_accepted_plan": True,
            "enable_background_investigation": enable_background_investigation,
        }
        initial_state["research_topic"] = user_input
        initial_state["clarified_research_topic"] = user_input

        # Only set clarification parameter if explicitly provided
        if enable_clarification is not None:
            initial_state["enable_clarification"] = enable_clarification

        if max_clarification_rounds is not None:
            initial_state["max_clarification_rounds"] = max_clarification_rounds

    config = {
        "configurable": {
            "thread_id": "default",
            "max_plan_iterations": max_plan_iterations,
            "max_step_num": max_step_num,
            "mcp_settings": {
                "servers": {
                    "pm-server": {
                        "transport": "sse",
                        "url": "http://pm_mcp_server:8080/sse",
                        "headers": {
                            "X-MCP-API-Key": os.getenv("PM_MCP_API_KEY", "mcp_a9b43d595b627e1e094209dea14bcb32f98867649ae181d4836dde87e283ccc3")
                        },
                        "enabled_tools": None,  # Enable all available PM tools
                        "add_to_agents": ["pm_agent"],  # Only PM Agent should have PM tools
                    },
                    "mcp-github-trending": {
                        "transport": "stdio",
                        "command": "uvx",
                        "args": ["mcp-github-trending"],
                        "enabled_tools": ["get_github_trending_repositories"],
                        "add_to_agents": ["researcher"],
                    }
                }
            },
        },
        "recursion_limit": get_recursion_limit(default=100),
    }
    last_message_cnt = 0
    final_state = None
    workflow_timeout = 300  # 5 minutes total timeout
    import time
    start_time = time.time()
    
    try:
        state_iteration = 0
        async for s in graph.astream(
            input=initial_state, config=config, stream_mode="values"
        ):
            state_iteration += 1
            # Check timeout on each iteration
            elapsed = time.time() - start_time
            if elapsed > workflow_timeout:
                logger.error(f"Workflow stream timed out after {workflow_timeout} seconds")
                break
            
            try:
                final_state = s
                # Yield intermediate states
                yield s
                if isinstance(s, dict) and "messages" in s:
                    if len(s["messages"]) <= last_message_cnt:
                        continue
                    last_message_cnt = len(s["messages"])
            except Exception as e:
                logger.error(f"Error processing stream output: {e}")
    except asyncio.TimeoutError:
        logger.error(f"Workflow stream timed out after {workflow_timeout} seconds")
        # Yield a final state indicating timeout
        if final_state:
            yield final_state
    except Exception as e:
        logger.error(f"Error in workflow stream: {e}", exc_info=True)
        # Yield final state if available
        if final_state:
            yield final_state

    # Check if clarification is needed using centralized logic
    if final_state and isinstance(final_state, dict):
        from backend.graph.nodes import needs_clarification

        if needs_clarification(final_state):
            # Don't handle clarification in streaming mode - just yield the state
            logger.warning("Clarification needed but not supported in streaming mode")
            yield final_state
            return

    logger.info("Streaming workflow completed successfully")


if __name__ == "__main__":
    print(graph.get_graph(xray=True).draw_mermaid())
