# ReAct: How LLM Sees Errors and Adapts

## What is ReAct?

**ReAct = Reasoning + Acting**

Paper: "ReAct: Synergizing Reasoning and Acting in Language Models" (2023)
Authors: Shunyu Yao et al., Google Brain & Princeton

### The Core Pattern

```
Thought → Action → Observation → Thought → Action → Observation → ...
  ↑                                  ↓
  └──────────── Loop ────────────────┘
```

**Key Insight:** The LLM sees EVERYTHING in the conversation history, including:
- Previous thoughts
- Actions taken
- **Observations (including errors)**
- And reasons about them in the next iteration

---

## How It Actually Works

### The Message History

```python
messages = [
    {"role": "system", "content": "You are an agent with tools..."},
    {"role": "user", "content": "Analyze sprint 5 for project 478"},
    
    # Iteration 1
    {"role": "assistant", "content": "Thought: I need to get sprint data first\nAction: get_sprint_report(sprint_id='5', project_id='478')"},
    {"role": "user", "content": "Observation: ERROR - Invalid UUID format. Expected UUID, got '478'"},
    
    # Iteration 2 - LLM SEES THE ERROR ABOVE
    {"role": "assistant", "content": "Thought: The error shows '478' is not a UUID. I need to resolve the project key first.\nAction: resolve_project_key(key='478')"},
    {"role": "user", "content": "Observation: {project_id: 'abc-123-uuid', project_key: '478', provider_id: 'uuid-456'}"},
    
    # Iteration 3 - LLM USES THE UUID
    {"role": "assistant", "content": "Thought: Now I have the UUID. Let me get the sprint report.\nAction: get_sprint_report(sprint_id='5', project_id='abc-123-uuid')"},
    {"role": "user", "content": "Observation: {sprint_data...}"}
]
```

**The "Magic":** The LLM sees the entire conversation, including the error observation, and adapts in the next thought!

---

## The ReAct Loop (Detailed)

### Code Implementation

```python
def react_agent(user_query, tools, max_iterations=10):
    """
    ReAct agent implementation.
    The LLM loops: Thought → Action → Observation
    """
    messages = [
        {"role": "system", "content": REACT_SYSTEM_PROMPT},
        {"role": "user", "content": user_query}
    ]
    
    for i in range(max_iterations):
        # 1. LLM generates Thought + Action
        response = llm.invoke(messages)
        
        # Parse response
        thought = extract_thought(response)
        action = extract_action(response)
        
        print(f"Iteration {i}")
        print(f"Thought: {thought}")
        print(f"Action: {action}")
        
        # If LLM decides it's done
        if action == "FINISH":
            return extract_answer(response)
        
        # 2. Execute Action
        observation = execute_tool(action, tools)
        
        print(f"Observation: {observation}")
        
        # 3. Add to conversation history (KEY PART!)
        messages.append({
            "role": "assistant",
            "content": f"Thought: {thought}\nAction: {action}"
        })
        messages.append({
            "role": "user",  # Observation as "user" message
            "content": f"Observation: {observation}"
        })
        
        # Loop continues - LLM will see the observation in next iteration
    
    return "Max iterations reached"
```

### System Prompt (ReAct)

```markdown
You are an agent that can use tools to solve tasks.

For each step, you MUST follow this format:

Thought: [Your reasoning about what to do next]
Action: [tool_name(arg1="value1", arg2="value2")]
Observation: [Will be filled by the system]

After seeing the observation, repeat the process.

If the observation shows an error:
- Think about why it failed
- Try a different approach
- Use a different tool if needed

When you have the final answer:
Thought: I now have enough information to answer
Action: FINISH
Answer: [Your final answer]

Available tools:
- list_sprints(project_id)
- get_sprint_report(sprint_id, project_id)
- resolve_project_key(key)
...
```

---

## Real Example: UUID Error Self-Correction

### Conversation Flow

```
User: "Analyze sprint 5 for project 478"

─────────── Iteration 1 ───────────

Assistant (LLM):
Thought: I need to get the sprint report to analyze it. 
The user mentioned project 478 and sprint 5.
Action: get_sprint_report(sprint_id="5", project_id="478")

System executes tool:
Observation: ERROR - psycopg2.errors.InvalidTextRepresentation: 
invalid input syntax for type uuid: "478"

─────────── Iteration 2 ───────────

Assistant (LLM) - SEES THE ERROR ABOVE:
Thought: The observation shows an error about UUID format. 
The project_id "478" is not a valid UUID, it's likely a 
project key or numeric ID. I should resolve it to a UUID first.
Action: resolve_project_key(key="478")

System executes tool:
Observation: {
  "project_id": "abc-123-uuid-456",
  "project_key": "478",
  "provider_id": "xyz-789-uuid"
}

─────────── Iteration 3 ───────────

Assistant (LLM) - SEES SUCCESSFUL RESOLUTION:
Thought: Great! Now I have the proper UUID (abc-123-uuid-456) 
for project 478. Let me get the sprint report using this UUID.
Action: get_sprint_report(sprint_id="5", project_id="abc-123-uuid-456")

System executes tool:
Observation: {
  "sprint": "Sprint 5",
  "status": "completed",
  "velocity": 25,
  "completed_story_points": 23,
  ...
}

─────────── Iteration 4 ───────────

Assistant (LLM) - HAS DATA, READY TO FINISH:
Thought: I now have all the sprint data. I can analyze and 
provide the final answer.
Action: FINISH
Answer: Based on the sprint report, Sprint 5 shows a velocity 
of 25 points with 23 points completed (92% completion rate)...
```

---

## The "Circular Loop" Explained

### Visual Representation

```
┌─────────────────────────────────────────────────┐
│                  LLM's Context                  │
│  [All previous thoughts, actions, observations] │
└────────────┬────────────────────────────────────┘
             │
             ↓
    ┌────────────────┐
    │  LLM Reasons   │ ← Sees ALL history including errors
    │   (Thought)    │
    └────────┬───────┘
             │
             ↓
    ┌────────────────┐
    │  LLM Acts      │
    │   (Action)     │
    └────────┬───────┘
             │
             ↓
    ┌────────────────┐
    │ Execute Tool   │
    │ (Observation)  │ ← Can be error or success
    └────────┬───────┘
             │
             ↓
    ┌────────────────────┐
    │ Add to History     │ ← Observation added to messages
    └────────┬───────────┘
             │
             ↓
    ┌────────────────────┐
    │ Loop Back to Top   │ ← LLM sees updated history
    └────────────────────┘
```

### Why It Works

**The LLM's "Memory" is the Conversation History:**

1. **Iteration 1:** LLM tries action X
2. **System:** Adds observation (error) to messages
3. **Iteration 2:** LLM receives ALL messages, including the error
4. **LLM Reasoning:** "Oh, I see an error about UUID. Let me try differently."
5. **System:** Adds new observation to messages
6. **Loop continues...**

---

## Comparison: ReAct vs Our Validator/Reflector

### ReAct (Implicit Validation)

```python
# Single loop, implicit validation
while not done:
    # LLM sees everything (including previous errors)
    thought_action = llm.invoke(all_messages)
    
    # Execute
    observation = execute(thought_action)
    
    # Add observation to history (LLM will see it next time)
    all_messages.append(observation)
```

**Pros:**
- ✅ Simple - one loop
- ✅ Fast - no separate validation node
- ✅ Flexible - LLM decides how to handle errors
- ✅ Natural - mimics human reasoning

**Cons:**
- ❌ No guaranteed reflection (LLM might ignore errors)
- ❌ No structured retry limits (could loop forever)
- ❌ Hard to monitor validation (buried in thoughts)
- ❌ No explicit replanning (just next action)

### Our Approach (Explicit Validation)

```python
# Multi-node, explicit validation
plan = planner()
for step in plan:
    result = execute(step)
    
    # Separate validation node
    validation = validator(result)  # ← Explicit
    
    if validation.failed:
        # Separate reflection node
        reflection = reflector(validation)  # ← Explicit
        
        # Separate replanning
        plan = planner(reflection)  # ← Explicit
```

**Pros:**
- ✅ Guaranteed validation (every step)
- ✅ Structured retry/replan (2 retries, 3 replans)
- ✅ Explicit reflection (forced analysis)
- ✅ Monitorable (clear logs, state tracking)

**Cons:**
- ❌ More complex - multiple nodes
- ❌ Slower - separate LLM calls for validation/reflection
- ❌ Over-engineered for simple tasks
- ❌ Less flexible - forced structure

---

## Which is "Better"?

### It Depends on the Use Case!

#### ReAct is Better For:

1. **Simple, interactive tasks**
   - "Book a restaurant"
   - "Search web and summarize"
   - "Answer questions with tools"

2. **When speed matters**
   - Single agent loop = faster
   - No separate validation nodes

3. **When LLM is reliable**
   - Modern LLMs (GPT-4, Claude-3.5) are good at self-correction
   - They naturally adapt when seeing errors

4. **Exploratory tasks**
   - LLM can flexibly decide approach
   - Not locked into a plan

**Example:** Claude in Cursor
```
You: "Refactor this function"
Claude: [reads file]
Claude: [tries edit]
Error: Syntax error
Claude: [sees error] "Let me fix the syntax"
Claude: [retries with fix] ✅ Success
```

#### Our Approach is Better For:

1. **Critical, high-stakes tasks**
   - Database writes
   - Financial transactions
   - Production deployments

2. **When explicit audit trail needed**
   - "Which step failed?"
   - "What was the reflection?"
   - "Why did it replan?"

3. **Complex, multi-step plans**
   - 5+ step workflows
   - Dependencies between steps
   - Need to ensure all steps validated

4. **Enterprise requirements**
   - Compliance (must validate)
   - Monitoring (track validation results)
   - Debugging (explicit state)

**Example:** Your PM Analysis
```
Task: "Comprehensive project analysis"
- 10+ steps
- Must validate data quality
- Need audit trail
- Critical for business decisions
```

---

## Hybrid Approach (Best of Both)

### Recommendation for Your System

```python
def coordinator_node(state):
    complexity = analyze_query_complexity(state)
    
    if complexity == "simple":
        # Use ReAct pattern (fast, implicit validation)
        return "react_agent"
    
    elif complexity == "medium":
        # Use ReAct with explicit validation at end
        return "react_agent_validated"
    
    else:  # complex
        # Use full pipeline (plan → validate → reflect → replan)
        return "planner"
```

### Implementation

```python
# Simple queries (80% of cases)
def react_agent_node(state):
    """
    Fast path: Single ReAct loop, no separate validation.
    For: "list tasks", "show projects", "get sprint 4"
    """
    tools = load_tools()
    agent = create_react_agent(llm, tools)
    
    result = agent.invoke(state["messages"])
    return {"messages": [result]}

# Medium queries (15% of cases)
def react_agent_validated_node(state):
    """
    ReAct + final validation.
    For: "analyze sprint 4", "team workload report"
    """
    tools = load_tools()
    agent = create_react_agent(llm, tools)
    
    result = agent.invoke(state["messages"])
    
    # Final validation after ReAct completes
    validation = validator.validate(result)
    if validation.failed:
        # Retry once with error context
        result = agent.invoke(state["messages"] + [validation.error])
    
    return {"messages": [result]}

# Complex queries (5% of cases)
def full_pipeline(state):
    """
    Full validation/reflection pipeline.
    For: "comprehensive project analysis", "create strategic plan"
    """
    # Your current implementation
    # Plan → Execute → Validate → Reflect → Replan
    ...
```

---

## ReAct in Modern Frameworks

### How LangChain Implements ReAct

```python
from langchain.agents import create_react_agent, AgentExecutor

# Create ReAct agent
agent = create_react_agent(
    llm=ChatOpenAI(model="gpt-4"),
    tools=tools,
    prompt=react_prompt  # Thought/Action/Observation format
)

executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,  # See the loop
    max_iterations=15,  # Prevent infinite loops
    handle_parsing_errors=True  # Graceful error handling
)

# Execute (loops automatically)
result = executor.invoke({"input": "Analyze sprint 5"})
```

**The Loop:**
```
Iteration 1:
  Thought: I need sprint data
  Action: get_sprint(5, "478")
  Observation: ERROR - UUID format

Iteration 2:
  Thought: Error shows I need UUID, let me resolve it
  Action: resolve_key("478")
  Observation: {uuid: "abc-123"}

Iteration 3:
  Thought: Got UUID, now get sprint
  Action: get_sprint(5, "abc-123")
  Observation: {data...}

Iteration 4:
  Thought: I have the data
  Action: FINISH
  Answer: [Analysis...]
```

---

## Conclusion: ReAct vs Explicit Validation

### ReAct is NOT "Better" - It's "Different"

**ReAct:**
- Simple, fast, flexible
- Good for: 80% of tasks (simple, interactive)
- Weakness: No guaranteed validation, can miss errors

**Your Explicit Approach:**
- Robust, structured, auditable
- Good for: 20% of tasks (complex, critical)
- Weakness: Over-engineered for simple tasks

### Recommendation

**Implement Both!**

```python
# Fast path: ReAct (for simple queries)
coordinator → react_agent → END

# Full path: Validator/Reflector (for complex queries)
coordinator → planner → agent → validator → reflector → planner
```

This gives you:
- ✅ Speed for simple queries (ReAct)
- ✅ Robustness for complex queries (Explicit validation)
- ✅ Best of both worlds

---

## Answer to Your Question

**"How can LLM see error and adapt in next thought?"**

**Answer:** The observation (including errors) is added to the conversation history as a message. In the next iteration, the LLM receives ALL previous messages, including the error observation, and can reason about it in its next "Thought".

```python
messages = [
    # Previous iteration
    {"role": "assistant", "content": "Action: do_something()"},
    {"role": "user", "content": "Observation: ERROR"}, # ← LLM sees this
    
    # Next iteration - LLM receives ALL above messages
    # LLM naturally includes the error in its context
    {"role": "assistant", "content": "Thought: I see the error, let me try differently"}
]
```

**The "circle loop":** 
Messages grow → LLM sees ALL → Reasons → Acts → Observation added → Messages grow → Loop

**Is ReAct better?**
Not "better" - **simpler and faster** for most tasks. Your explicit approach is **more robust** for critical tasks.

**Best solution:** Use both! ReAct for simple, your approach for complex. 🎯


