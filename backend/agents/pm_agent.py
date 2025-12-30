"""
LLM-Driven PM Agent

A ReAct-style agent that handles all PM queries through LLM reasoning.
No hardcoded patterns - all decisions made by LLM.

Flow:
1. THINK: LLM analyzes the query and plans approach
2. ACT: LLM calls appropriate tool(s)
3. OBSERVE: LLM sees tool result
4. DECIDE: LLM decides if done or needs more steps
5. REPEAT until done (max steps limit)
"""
import json
import logging
import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)


@dataclass
class AgentStep:
    """A single step in the agent's execution."""
    type: str  # "thinking", "tool_call", "tool_result", "decision"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class AgentResult:
    """Final result from the agent."""
    success: bool
    result: str
    steps: List[AgentStep]
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Any]  # Added: Full tool outputs
    final_answer: str


class LLMDrivenPMAgent:
    """
    LLM-driven PM Agent using ReAct pattern.
    
    All decisions are made by the LLM, no hardcoded rules.
    """
    
    def __init__(
        self,
        llm,
        tools: List[BaseTool],
        project_id: str,
        max_steps: int = 5,
        on_tool_result: Optional[Any] = None  # Callback for real-time streaming
    ):
        self.llm = llm
        self.tools = tools
        self.project_id = project_id
        self.max_steps = max_steps
        self.on_tool_result = on_tool_result  # PLAN 9: Callback for real-time tool result streaming
        self.steps: List[AgentStep] = []
        self.tool_results: List[Tuple[str, str, str]] = []  # (tool_name, args, result)
    
    def _get_system_prompt(self) -> str:
        """Build the system prompt for the agent."""
        tool_descriptions = "\n".join([
            f"- **{tool.name}**: {tool.description[:200]}..."
            for tool in self.tools
        ])
        
        return f"""You are a Project Management AI Assistant that helps users with PM tasks.

## Your Capabilities
You have access to these tools:
{tool_descriptions}

## Current Context
- **Project ID**: `{self.project_id}`
- Always use this project_id when calling tools that require it.

## How You Work (ReAct Pattern)

For each user request, you will:

1. **THINK**: Analyze what the user wants and plan your approach
   - Consider what information is needed
   - Which tool(s) might help
   - What order to execute them

2. **ACT**: Call the appropriate tool
   - Use the tool that best addresses the current need
   - Pass the correct parameters

3. **OBSERVE**: Examine the tool result
   - Did it return the expected data?
   - Is there enough information to answer the user?

4. **DECIDE**: Determine next steps
   - If you have enough info → Summarize and respond
   - If you need more data → Call another tool
   - If there's an error → Try a different approach

## Important Guidelines
- You can call multiple tools if needed to fully answer a question
- Always aim to provide complete, actionable information
- If data is large, summarize the key points
- For analysis requests (e.g., "who is overloaded"), process the data yourself
- Be concise but thorough in your final response

## Output Format
When you have your final answer, provide a clear, well-formatted response.
Use tables for structured data. Use bullet points for lists.
"""

    async def _think(self, user_query: str, conversation: List) -> str:
        """Let LLM think about the query."""
        think_prompt = f"""Based on this conversation and the user's request, think step by step:

1. What is the user asking for?
2. What information do I need to answer this?
3. Which tool(s) should I use?
4. What parameters should I pass?

User Request: {user_query}

IMPORTANT: 
- Do NOT generate fake data, placeholder content, or example responses.
- Do NOT write out tables or lists with made-up values.
- Only describe your plan briefly, then proceed to call the appropriate tool."""

        conversation.append(HumanMessage(content=think_prompt))
        
        # Get LLM's thinking (without tool calls for this step)
        response = await self.llm.ainvoke(conversation)
        thinking = response.content
        
        self.steps.append(AgentStep(
            type="thinking",
            content=thinking[:5000],  # Increased truncation for UI
            metadata={"full_length": len(thinking)}
        ))
        
        logger.info(f"[PM-AGENT] 🧠 THINKING: {thinking[:200]}...")
        
        return thinking
    
    async def _act(self, user_query: str, conversation: List) -> Optional[Tuple[str, Dict, str]]:
        """Execute a tool call."""
        # Bind tools and invoke
        llm_with_tools = self.llm.bind_tools(self.tools, tool_choice="auto")
        
        response = await llm_with_tools.ainvoke(conversation)
        
        if not hasattr(response, 'tool_calls') or not response.tool_calls:
            # No tool call - LLM is providing final answer
            return None
        
        tool_call = response.tool_calls[0]
        tool_name = tool_call['name']
        tool_args = tool_call['args']
        tool_call_id = tool_call['id']
        
        # Inject project_id if needed
        if 'project_id' not in tool_args or not tool_args.get('project_id'):
            tool_args['project_id'] = self.project_id
        
        self.steps.append(AgentStep(
            type="tool_call",
            content=f"{tool_name}({json.dumps(tool_args)})",
            metadata={"tool": tool_name, "args": tool_args, "id": tool_call_id}
        ))
        
        logger.info(f"[PM-AGENT] 🔧 TOOL CALL: {tool_name}({tool_args})")
        
        # Execute tool
        tool_result = None
        for tool in self.tools:
            if tool.name == tool_name:
                tool_result = await tool.ainvoke(tool_args)
                break
        
        if tool_result is None:
            tool_result = f"Error: Tool '{tool_name}' not found"
        
        result_str = str(tool_result)
        
        # PLAN 9: Call callback for real-time streaming
        if self.on_tool_result:
            try:
                await self.on_tool_result(tool_name, tool_call_id, result_str)
            except Exception as e:
                logger.error(f"[PM-AGENT] Error in tool result callback: {e}")
        
        self.steps.append(AgentStep(
            type="tool_result",
            content=result_str,
            metadata={"tool": tool_name, "length": len(result_str), "id": tool_call_id}
        ))
        
        self.tool_results.append((tool_name, json.dumps(tool_args), result_str))
        
        logger.info(f"[PM-AGENT] 📋 TOOL RESULT: {len(result_str)} chars")
        
        return tool_name, tool_args, result_str, tool_call_id
    
    async def _decide(self, user_query: str, tool_result: str, conversation: List) -> Tuple[bool, str]:
        """Let LLM decide if we're done or need more steps."""
        decide_prompt = f"""Based on the tool result, decide:

1. Does this result fully answer the user's question: "{user_query}"?
2. Do I need to call another tool for more information?
3. Do I need to analyze/process this data further?

If you have enough information, provide your final answer now.
If you need more data, explain what you need and call another tool.

Be concise and actionable."""

        conversation.append(HumanMessage(content=decide_prompt))
        
        # Check if LLM wants to call another tool
        llm_with_tools = self.llm.bind_tools(self.tools, tool_choice="auto")
        response = await llm_with_tools.ainvoke(conversation)
        
        if hasattr(response, 'tool_calls') and response.tool_calls:
            # LLM wants to call another tool
            self.steps.append(AgentStep(
                type="decision",
                content="Need more information, calling another tool",
                metadata={"action": "continue"}
            ))
            logger.info(f"[PM-AGENT] 🔄 DECISION: Need more info, continuing...")
            return False, ""
        
        # LLM is done - this is the final answer
        final_answer = response.content
        
        self.steps.append(AgentStep(
            type="decision",
            content="Complete - providing final answer",
            metadata={"action": "done"}
        ))
        
        logger.info(f"[PM-AGENT] ✅ DECISION: Complete")
        
        return True, final_answer
    
    async def run(self, user_query: str) -> AgentResult:
        """
        Run the agent on a user query.
        
        Returns AgentResult with success status, result, and all steps.
        """
        logger.info(f"[PM-AGENT] 🚀 Starting agent for: {user_query[:100]}...")
        
        # Build initial conversation
        system_msg = SystemMessage(content=self._get_system_prompt())
        user_msg = HumanMessage(content=user_query)
        conversation = [system_msg, user_msg]
        
        final_result = ""
        all_tool_calls = []
        all_tool_outputs = [] # Capture actual results
        
        for step in range(self.max_steps):
            step_ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            logger.info(f"[{step_ts}] [PM-AGENT] 📍 Step {step + 1}/{self.max_steps}")
            
            # THINK: Initial reasoning before first action
            # This captures the agent's analysis and planning for the UI
            if step == 0:
                think_ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                logger.info(f"[{think_ts}] [PM-AGENT] 🧠 Starting initial thinking phase...")
                await self._think(user_query, conversation)
            
            # ACT: Try to call a tool
            act_result = await self._act(user_query, conversation)
            
            if act_result is None:
                # No tool call - LLM is providing final answer directly
                llm_response = await self.llm.ainvoke(conversation)
                final_result = llm_response.content
                break
            
            tool_name, tool_args, tool_result, tool_call_id = act_result
            all_tool_calls.append({
                "result_length": len(tool_result)
            })
            all_tool_outputs.append(tool_result)
            
            # Add tool call and result to conversation
            conversation.append(AIMessage(
                content="",
                tool_calls=[{"id": tool_call_id, "name": tool_name, "args": tool_args}]
            ))
            conversation.append(ToolMessage(
                content=tool_result[:50000],  # Limit for context
                tool_call_id=tool_call_id,
                name=tool_name
            ))
            
            # DECIDE: Check if we're done
            is_done, final_answer = await self._decide(user_query, tool_result, conversation)
            
            if is_done:
                final_result = final_answer or tool_result
                break
        
        # Build final result
        if not final_result:
            # Max steps reached without final answer
            if self.tool_results:
                final_result = self.tool_results[-1][2]  # Last tool result
            else:
                final_result = "Unable to complete the request within the allowed steps."
        
        logger.info(f"[PM-AGENT] 🏁 Agent complete with {len(self.steps)} steps")
        
        return AgentResult(
            success=True,
            result=final_result,
            steps=self.steps,
            tool_calls=all_tool_calls,
            tool_results=all_tool_outputs,
            final_answer=final_result
        )
    
    def get_thoughts_for_ui(self) -> List[Dict[str, Any]]:
        """Convert steps to thoughts format for UI display."""
        thoughts = []
        for i, step in enumerate(self.steps):
            emoji = {
                "thinking": "🧠",
                "tool_call": "🔧",
                "tool_result": "📋",
                "decision": "✅" if step.metadata.get("action") == "done" else "🔄"
            }.get(step.type, "•")
            
            thoughts.append({
                "thought": f"{emoji} {step.type.upper()}: {step.content[:5000]}",
                "before_tool": step.type in ["thinking", "tool_call"],
                "step_index": i,
                "step_type": step.type,
                "timestamp": step.timestamp
            })
        
        return thoughts


async def run_pm_agent(
    llm,
    tools: List[BaseTool],
    user_query: str,
    project_id: str,
    max_steps: int = 5,
    on_tool_result: Optional[Any] = None  # PLAN 9: Callback for real-time streaming
) -> AgentResult:
    """
    Convenience function to run the PM agent.
    
    Args:
        llm: LangChain LLM instance
        tools: List of PM tools
        user_query: User's question/request
        project_id: Current project ID
        max_steps: Maximum iterations
        on_tool_result: Async callback for real-time tool result streaming
    
    Returns:
        AgentResult with success status, result, and steps
    """
    agent = LLMDrivenPMAgent(
        llm=llm,
        tools=tools,
        project_id=project_id,
        max_steps=max_steps,
        on_tool_result=on_tool_result
    )
    
    return await agent.run(user_query)

