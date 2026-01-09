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
from backend.agents.global_context_optimizer import GlobalContextOptimizer

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
        thread_id: str = "unknown",
        max_steps: int = 5,
        on_tool_result: Optional[Any] = None  # Callback for real-time streaming
    ):
        self.llm = llm
        self.tools = tools
        self.project_id = project_id
        self.thread_id = thread_id
        self.max_steps = max_steps
        self.on_tool_result = on_tool_result  # PLAN 9: Callback for real-time tool result streaming
        self.steps: List[AgentStep] = []
        self.tool_results: List[Tuple[str, str, str]] = []  # (tool_name, args, result)
        self.global_optimizer = GlobalContextOptimizer()  # NEW: Global Optimizer instance
    
    def _get_system_prompt(self) -> str:
        """Build the system prompt for the agent."""
        tool_descriptions = "\n".join([
            f"- **{tool.name}**: {tool.description[:200]}..."
            for tool in self.tools
        ])
        
        return f"""You are a Project Management AI Assistant that helps users with PM tasks.

## CRITICAL RULES (Name vs ID)
- **NEVER guess IDs based on names.**
- If a user mentions a name (e.g., "Sprint 4", "Alpha Project"), you MUST ID it first.
- Example: User says "Sprint 4". You MUST call `list_sprints` to find the ID of "Sprint 4".
- DO NOT assume "Sprint 4" means `sprint_id="4"`. That is almost always WRONG.
- **Protocol**:
  1. Call `list_sprints` (or similar list tool) to find the entity.
  2. Extract the correct ID from the list result.
  3. Call the specific tool (e.g., `get_sprint`) with the confirmed ID.

## Your Capabilities
You have access to these tools:
{tool_descriptions}

## Current Context
- **Project ID**: `{self.project_id}`
- Always use this project_id when calling tools that require it.

## 📊 Report Templates - FOLLOW EXACTLY

### 1. WEEKLY STATUS REPORT / PROJECT REPORT
**Trigger words:** "weekly report", "project report", "status report", "this week"
**Tools to call (in order):**
1. `list_sprints(project_id)` - Get current active sprint
2. `list_tasks(project_id, sprint_id)` - Get all tasks in current sprint

**DO NOT call:** `get_current_user` (this is PROJECT report, not personal)

**Output format:**
```
## Weekly Status Report - [Date Range]

### 📊 Overall Status: [GREEN/YELLOW/RED]

### ✅ Accomplishments This Week
- [List completed tasks]

### 🔄 In Progress
- [List tasks in progress with assignees]

### ⚠️ Blockers & Issues
- [List blocked tasks if any]

### 📈 Sprint Progress
- Completed: X tasks
- In Progress: Y tasks
- Remaining: Z tasks

### 📅 Next Week Focus
- [Key priorities]
```

---

### 2. SPRINT REPORT
**Trigger words:** "sprint report", "sprint summary", "sprint [number]"
**Tools to call:**
1. `list_sprints(project_id)` - Find the sprint
2. `sprint_report(sprint_id, project_id)` - Get sprint metrics
3. `burndown_chart(sprint_id, project_id)` - Optional for progress visualization

**Output format:**
```
## Sprint [Name] Report

### Sprint Info
- Duration: [Start] to [End]
- Goal: [Sprint goal]

### 📊 Metrics
- Story Points Committed: X
- Story Points Completed: Y
- Completion Rate: Z%

### ✅ Completed Items
[List completed user stories/tasks]

### ❌ Not Completed
[List items that didn't make it]

### 🔍 Retrospective Notes
- What went well
- What to improve
```

---

### 3. RESOURCE/WORKLOAD REPORT
**Trigger words:** "resource", "workload", "allocation", "who is working on", "team capacity", "overloaded"
**Tools to call:**
1. `list_users(project_id)` - Get team members
2. `work_distribution_chart(project_id, dimension='assignee')` - Get workload distribution
3. OR `list_tasks_by_assignee(project_id, assignee_id)` - For specific user

**Output format:**
```
## Team Workload Report

### 👥 Team Capacity Overview
| Team Member | Assigned Tasks | Status |
|-------------|----------------|--------|
| [Name]      | X tasks        | [OK/Overloaded/Underutilized] |

### ⚠️ Attention Required
- [Anyone with too many tasks]
- [Anyone with no tasks]

### 📊 Work Distribution
[Summary of balance]
```

---

### 4. MY PERSONAL REPORT
**Trigger words:** "my tasks", "my work", "my worklogs", "assigned to me"
**Tools to call:**
1. `get_current_user(project_id)` - Get current user
2. `list_tasks_by_assignee(project_id, assignee_id)` - Get their tasks

**Output format:**
```
## My Task Summary

### 📋 My Current Tasks
[List tasks assigned to user]

### ✅ My Completed Work
[Recently completed items]
```

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
- Always aim to provide complete, actionable information. **List all relevant items found.**
- For analysis requests (e.g., "who is overloaded"), process the data yourself
- Be concise but thorough in your final response

## Handling Missing Data
- If a user asks for a specific report (e.g., Sprint Report) and you cannot find key metrics (e.g., story points, velocity) from the tools:
  1. **Do NOT** output a partial report that looks "normal".
  2. **Do NOT** make up numbers.
  3. **DO** explicitly state what is missing.
  4. **DO** ask the user if they want to proceed with a partial report or if they can provide the missing data sources.
  5. **Better yet**: Try to find the data using a different tool (e.g., `list_tasks` often has status/points even if `sprint_report` fails).

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
        
        # 🟢 OPTIMIZATION: Assemble context using Global Logic
        current_history = [msg for msg in conversation if isinstance(msg, (SystemMessage, HumanMessage, AIMessage, ToolMessage))]
        # We need to exclude the system prompt if we are passing specific parts, but conversation includes it.
        # GlobalContextOptimizer splits it. Ideally we pass the raw history parts.
        
        # Let's extract system_prompt and rest
        sys_msg_content = self._get_system_prompt()
        history_msgs = conversation[1:] # Skip first system message assuming it's linear.
        
        # Assemble fully optimized context
        optimized_conversation = self.global_optimizer.assemble_context(
            thread_id=self.thread_id,
            user_query=user_query,
            system_prompt=sys_msg_content,
            history=history_msgs
        )
        
        # Get LLM's thinking (without tool calls for this step)
        response = await self.llm.ainvoke(optimized_conversation)
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
        
        # ALWAYS inject the canonical project_id from context
        # The LLM sometimes extracts partial IDs from tool results (e.g., "478" instead of "uuid:478")
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
        
        # OPTIMIZATION: Reduce result size if too large
        optimized_result = await self.global_optimizer.optimize_tool_result(tool_name, result_str, user_query)
        
        self.steps.append(AgentStep(
            type="tool_result",
            content=optimized_result, # Store optimized result
            metadata={"tool": tool_name, "length": len(optimized_result), "original_length": len(result_str), "id": tool_call_id}
        ))
        
        
        self.tool_results.append((tool_name, json.dumps(tool_args), optimized_result))
        
        logger.info(f"[PM-AGENT] 📋 TOOL RESULT: {len(result_str)} -> {len(optimized_result)} chars")
        logger.info(f"[COUNTER-DEBUG] {datetime.datetime.now().isoformat()} pm_agent captured: tool={tool_name}, result_len={len(result_str)}")
        
        return tool_name, tool_args, result_str, tool_call_id
    
    async def _decide(self, user_query: str, tool_result: str, conversation: List) -> Tuple[bool, str]:
        """Let LLM decide if we're done or need more steps."""
        
        # Build summary of already-called tools to prevent duplicate calls
        called_tools_summary = ""
        if self.tool_results:
            called_tools_summary = "\n\n## IMPORTANT: Tools Already Called (DO NOT REPEAT)\n"
            for tool_name, tool_args, result in self.tool_results:
                result_preview = result[:200] + "..." if len(result) > 200 else result
                called_tools_summary += f"- **{tool_name}**({tool_args}): {len(result)} chars\n"
            called_tools_summary += "\n⚠️ Do NOT call the same tool with the same arguments again - you already have that data!\n"
        
        decide_prompt = f"""Based on the tool result, decide:

1. Does this result fully answer the user's question: "{user_query}"?
2. Do I need to call ANOTHER tool (with DIFFERENT parameters) for more information?
3. Do I need to analyze/process this data further?
{called_tools_summary}
If you have enough information, provide your final answer now.
If you need more data (e.g., missing metrics for a report), call a DIFFERENT tool or use DIFFERENT parameters.
**CRITICAL**: If the user asked for a REPORT (Sprint/Weekly) and you are missing data (like story points or completion rate), do NOT just provide a partial list. Try to calculate it from `list_tasks` or call another tool. If you truly cannot find it, state that explicitly.

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
        logger.info(f"[COUNTER-DEBUG] {datetime.datetime.now().isoformat()} get_thoughts_for_ui called with {len(self.steps)} steps")
        thoughts = []
        for i, step in enumerate(self.steps):
            emoji = {
                "thinking": "🧠",
                "tool_call": "🔧",
                "tool_result": "📋",
                "decision": "✅" if step.metadata.get("action") == "done" else "🔄"
            }.get(step.type, "•")
            
            # For tool_result, parse content to extract count
            if step.type == "tool_result":
                tool_name = step.metadata.get("tool", "tool")
                result_count_info = ""
                try:
                    result_data = json.loads(step.content)
                    if isinstance(result_data, dict):
                        if "tasks" in result_data and isinstance(result_data["tasks"], list):
                            result_count_info = f" → {len(result_data['tasks'])} tasks"
                        elif "sprints" in result_data and isinstance(result_data["sprints"], list):
                            result_count_info = f" → {len(result_data['sprints'])} sprints"
                        elif "users" in result_data and isinstance(result_data["users"], list):
                            result_count_info = f" → {len(result_data['users'])} users"
                        elif "projects" in result_data and isinstance(result_data["projects"], list):
                            result_count_info = f" → {len(result_data['projects'])} projects"
                        elif "sprint" in result_data and isinstance(result_data["sprint"], dict):
                            sprint_name = result_data["sprint"].get("name", "")
                            result_count_info = f" → {sprint_name}" if sprint_name else ""
                        elif "success" in result_data:
                            if result_data["success"]:
                                result_count_info = " ✓"
                            else:
                                error = result_data.get("error", "")[:40]
                                result_count_info = f" ✗ {error}" if error else " ✗"
                except (json.JSONDecodeError, KeyError, TypeError):
                    pass
                
                thought_text = f"{emoji} {tool_name}{result_count_info}"
                logger.info(f"[COUNTER-DEBUG] {datetime.datetime.now().isoformat()} tool_result thought: {thought_text}")
            else:
                thought_text = f"{emoji} {step.type.upper()}: {step.content[:5000]}"
            
            thoughts.append({
                "thought": thought_text,
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
    thread_id: str = "unknown",
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
        thread_id: Conversation ID for context optimization
        max_steps: Maximum iterations
        on_tool_result: Async callback for real-time tool result streaming
    
    Returns:
        AgentResult with success status, result, and steps
    """
    agent = LLMDrivenPMAgent(
        llm=llm,
        tools=tools,
        project_id=project_id,
        thread_id=thread_id,
        max_steps=max_steps,
        on_tool_result=on_tool_result
    )
    
    return await agent.run(user_query)

