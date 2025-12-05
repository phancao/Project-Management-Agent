# Intelligent Routing: How to Determine Query Complexity

## The Problem

```python
def coordinator_node(state):
    if is_simple_query(state):  # ← HOW does this work?
        return "react_agent"
    else:
        return "planner"
```

**You're right:** A hardcoded check would be brittle and dumb!

---

## Solution 1: LLM-Based Classification (Recommended)

### Use the LLM to Classify Query Complexity

```python
async def coordinator_node(state: State, config: RunnableConfig) -> Command:
    """
    Uses LLM to intelligently classify query complexity.
    Fast single LLM call (100-200ms) to determine routing.
    """
    user_query = get_last_user_message(state)
    
    classification_prompt = f"""Classify this user query's complexity for a PM system.

Query: "{user_query}"

Consider:
- Simple: Single action, direct answer (list, show, get)
- Medium: Analysis, comparison, calculations on existing data
- Complex: Multi-step research, external search, strategic planning

Respond with ONLY one word: SIMPLE, MEDIUM, or COMPLEX

Examples:
- "List my tasks" → SIMPLE
- "Show sprint 4" → SIMPLE  
- "What's the velocity of sprint 5?" → MEDIUM
- "Analyze sprint 5 performance" → MEDIUM
- "Comprehensive project analysis with industry research" → COMPLEX
- "Research agile best practices and create implementation plan" → COMPLEX

Classification:"""

    # Fast classification (single LLM call, ~100-200ms)
    llm = get_llm_by_type("basic")
    response = await llm.ainvoke(classification_prompt)
    classification = response.content.strip().upper()
    
    logger.info(f"[COORDINATOR] Query classified as: {classification}")
    
    if classification == "SIMPLE":
        # Fast path: Direct agent, no planning
        return Command(goto="react_agent")
    
    elif classification == "MEDIUM":
        # Medium path: Planning but skip some validation
        return Command(
            update={"validation_mode": "light"},
            goto="planner"
        )
    
    else:  # COMPLEX
        # Full path: Complete planning + validation + reflection
        return Command(
            update={"validation_mode": "full"},
            goto="planner"
        )
```

**Pros:**
- ✅ Intelligent - LLM understands intent
- ✅ Flexible - Adapts to new query types
- ✅ Fast - Single LLM call (~100-200ms)
- ✅ No hardcoding

**Cons:**
- ⚠️ Extra LLM call (but very fast)
- ⚠️ Cost (but minimal for classification)

---

## Solution 2: Structured LLM Classification

### Use JSON Mode for Reliable Classification

```python
from pydantic import BaseModel, Field

class QueryClassification(BaseModel):
    """Structured classification of user query."""
    complexity: Literal["simple", "medium", "complex"] = Field(
        description="Query complexity level"
    )
    reasoning: str = Field(
        description="Brief explanation of classification"
    )
    estimated_steps: int = Field(
        description="Estimated number of steps needed"
    )
    requires_external_data: bool = Field(
        description="Whether query needs web search or external data"
    )

async def coordinator_node(state: State, config: RunnableConfig) -> Command:
    """Uses structured LLM output for reliable classification."""
    user_query = get_last_user_message(state)
    
    classification_prompt = f"""Analyze this user query for a PM system:

Query: "{user_query}"

Classify based on:
1. **Complexity**: 
   - simple: Single tool call, direct answer
   - medium: Multiple tool calls, analysis/calculation
   - complex: Multi-step planning, research, strategic work

2. **Steps**: How many steps needed (1 = simple, 2-5 = medium, 6+ = complex)

3. **External Data**: Does it need web search or just PM data?

Respond in JSON format."""

    # Use structured output
    llm = get_llm_by_type("basic").with_structured_output(QueryClassification)
    classification = await llm.ainvoke(classification_prompt)
    
    logger.info(f"[COORDINATOR] Classification: {classification.complexity}")
    logger.info(f"[COORDINATOR] Reasoning: {classification.reasoning}")
    logger.info(f"[COORDINATOR] Estimated steps: {classification.estimated_steps}")
    
    # Route based on structured classification
    if classification.complexity == "simple" and not classification.requires_external_data:
        return Command(goto="react_agent")
    
    elif classification.complexity == "medium":
        return Command(
            update={"estimated_steps": classification.estimated_steps},
            goto="planner"
        )
    
    else:
        return Command(
            update={
                "estimated_steps": classification.estimated_steps,
                "requires_external_data": classification.requires_external_data
            },
            goto="planner"
        )
```

**Example Output:**
```json
{
  "complexity": "medium",
  "reasoning": "Query requires analyzing sprint data (2-3 tool calls) and generating insights, but no external research needed",
  "estimated_steps": 3,
  "requires_external_data": false
}
```

---

## Solution 3: Adaptive Routing (Start Simple, Escalate)

### Start with ReAct, Escalate if Needed

```python
def react_agent_with_escalation(state: State) -> Command:
    """
    Start with ReAct, but escalate to full pipeline if:
    - Too many iterations (5+)
    - Tool failures detected
    - Agent explicitly requests planning
    """
    max_react_iterations = 5
    
    # Run ReAct agent
    agent = create_react_agent(llm, tools)
    
    for i in range(max_react_iterations):
        result = agent.step(state)
        
        # Check if agent is struggling
        if i >= 3 and has_repeated_failures(result):
            logger.info("[REACT] Escalating to full planner - multiple failures detected")
            return Command(
                update={"escalation_reason": "repeated_failures"},
                goto="planner"
            )
        
        # Check if agent requests planning
        if "I need to plan" in result.thought or "complex task" in result.thought:
            logger.info("[REACT] Escalating to full planner - agent requested planning")
            return Command(
                update={"escalation_reason": "agent_requested"},
                goto="planner"
            )
        
        # Check if done
        if result.action == "FINISH":
            return Command(
                update={"messages": [result.answer]},
                goto="END"
            )
    
    # Hit max iterations - escalate
    logger.info("[REACT] Escalating to full planner - max iterations reached")
    return Command(
        update={"escalation_reason": "max_iterations"},
        goto="planner"
    )
```

**Pros:**
- ✅ No upfront classification
- ✅ Automatically adapts
- ✅ Efficient (only escalates when needed)

**Cons:**
- ⚠️ Wasted iterations if it needs to escalate
- ⚠️ More complex logic

---

## Solution 4: Hybrid Heuristics + LLM

### Fast Heuristics First, LLM for Uncertain Cases

```python
async def coordinator_node(state: State, config: RunnableConfig) -> Command:
    """
    Uses fast heuristics for obvious cases,
    LLM classification for ambiguous cases.
    """
    user_query = get_last_user_message(state)
    query_lower = user_query.lower()
    
    # Fast heuristic checks (no LLM call)
    
    # 1. Obvious SIMPLE patterns
    simple_patterns = [
        r"^list (my )?tasks?$",
        r"^show (me )?(project|sprint|task)",
        r"^get (project|sprint|task)",
        r"^what (is|are) (my|the)",
    ]
    if any(re.match(pattern, query_lower) for pattern in simple_patterns):
        logger.info("[COORDINATOR] Fast heuristic: SIMPLE (pattern match)")
        return Command(goto="react_agent")
    
    # 2. Obvious COMPLEX indicators
    complex_keywords = [
        "comprehensive", "complete", "full analysis",
        "research", "investigate", "explore",
        "industry trends", "best practices",
        "strategic plan", "roadmap"
    ]
    if any(keyword in query_lower for keyword in complex_keywords):
        logger.info("[COORDINATOR] Fast heuristic: COMPLEX (keyword match)")
        return Command(goto="planner")
    
    # 3. Ambiguous - use LLM classification
    logger.info("[COORDINATOR] Ambiguous query - using LLM classification")
    classification = await classify_with_llm(user_query)
    
    if classification == "SIMPLE":
        return Command(goto="react_agent")
    else:
        return Command(goto="planner")


async def classify_with_llm(query: str) -> str:
    """LLM classification for ambiguous queries."""
    prompt = f"""Is this PM query simple or complex?

Query: "{query}"

Simple = Single action (list, show, get)
Complex = Analysis, planning, multiple steps

Respond: SIMPLE or COMPLEX"""

    llm = get_llm_by_type("basic")
    response = await llm.ainvoke(prompt)
    return response.content.strip().upper()
```

**Pros:**
- ✅ Fast for obvious cases (no LLM call)
- ✅ Intelligent for ambiguous cases
- ✅ Best of both worlds

**Cons:**
- ⚠️ Need to maintain heuristics
- ⚠️ Heuristics can become brittle

---

## Solution 5: Few-Shot Classification

### Use Few-Shot Examples for Better Accuracy

```python
async def coordinator_node(state: State, config: RunnableConfig) -> Command:
    """Uses few-shot examples for accurate classification."""
    user_query = get_last_user_message(state)
    
    few_shot_prompt = f"""Classify PM query complexity based on these examples:

SIMPLE (1 step, direct answer):
- "List my tasks"
- "Show sprint 4"
- "What is project 478?"
- "Get task 123"

MEDIUM (2-5 steps, analysis):
- "Analyze sprint 5 performance"
- "What's the team velocity?"
- "Compare sprint 4 and sprint 5"
- "Show resource allocation"

COMPLEX (6+ steps, research, planning):
- "Comprehensive project health analysis"
- "Research agile best practices and create implementation plan"
- "Strategic roadmap for next quarter"
- "Full team performance review with recommendations"

Now classify this query:
"{user_query}"

Classification (SIMPLE/MEDIUM/COMPLEX):"""

    llm = get_llm_by_type("basic")
    response = await llm.ainvoke(few_shot_prompt)
    classification = response.content.strip().upper()
    
    logger.info(f"[COORDINATOR] Few-shot classification: {classification}")
    
    # Route based on classification
    routing_map = {
        "SIMPLE": "react_agent",
        "MEDIUM": "planner",  # Could use lighter validation
        "COMPLEX": "planner"
    }
    
    return Command(goto=routing_map.get(classification, "planner"))
```

**Pros:**
- ✅ More accurate (examples guide LLM)
- ✅ Easy to tune (add more examples)
- ✅ Transparent (examples show logic)

**Cons:**
- ⚠️ Still requires LLM call
- ⚠️ Prompt gets longer

---

## Comparison Table

| Approach | Speed | Accuracy | Maintenance | Cost |
|----------|-------|----------|-------------|------|
| **LLM Classification** | Fast (100ms) | High | Low | ~$0.0001/query |
| **Structured LLM** | Fast (150ms) | Very High | Low | ~$0.0002/query |
| **Adaptive (Escalate)** | Variable | High | Medium | Variable |
| **Heuristics + LLM** | Very Fast | High | High | Low |
| **Few-Shot LLM** | Fast (120ms) | Very High | Low | ~$0.0001/query |

---

## Recommended Implementation

### Option 1: LLM Classification (Best Balance)

```python
async def coordinator_node(state: State, config: RunnableConfig) -> Command:
    """
    Intelligent coordinator using LLM classification.
    
    Cost: ~$0.0001 per query (100 tokens @ $0.001/1k)
    Time: ~100-200ms
    """
    user_query = get_last_user_message(state)
    
    # Single fast LLM call for classification
    classification_prompt = f"""Classify this PM query:

Query: "{user_query}"

SIMPLE: Direct data retrieval (list, show, get)
MEDIUM: Analysis or calculations on PM data
COMPLEX: Multi-step planning, research, or strategy

Respond with ONE WORD: SIMPLE, MEDIUM, or COMPLEX"""

    llm = get_llm_by_type("basic")
    response = await llm.ainvoke(classification_prompt)
    classification = response.content.strip().upper()
    
    logger.info(f"[COORDINATOR] 🎯 Query classified: {classification}")
    
    # Route intelligently
    if classification == "SIMPLE":
        logger.info("[COORDINATOR] ⚡ Fast path: ReAct agent")
        return Command(
            update={"routing_mode": "fast"},
            goto="react_agent"
        )
    
    elif classification == "MEDIUM":
        logger.info("[COORDINATOR] 📊 Medium path: Planning with light validation")
        return Command(
            update={"routing_mode": "medium", "validation_mode": "light"},
            goto="planner"
        )
    
    else:  # COMPLEX
        logger.info("[COORDINATOR] 🔬 Full path: Complete pipeline")
        return Command(
            update={"routing_mode": "full", "validation_mode": "full"},
            goto="planner"
        )
```

### Why This is NOT Hardcoded

```python
# ❌ Hardcoded (brittle, dumb)
if "list" in query or "show" in query:
    return "simple"

# ✅ LLM-based (intelligent, flexible)
classification = llm.classify(query)
# LLM understands:
# - "Give me all tasks" → SIMPLE (same as "list tasks")
# - "Show me a detailed breakdown" → MEDIUM (not simple despite "show")
# - "List tasks and analyze velocity" → MEDIUM (not simple despite "list")
```

---

## Real Examples

### Example 1: Ambiguous Query

```
Query: "Show me sprint 5"

Hardcoded check: "show" → SIMPLE ✅ Correct

Query: "Show me comprehensive sprint 5 analysis"

Hardcoded check: "show" → SIMPLE ❌ Wrong!
LLM classification: COMPLEX ✅ Correct (understands "comprehensive analysis")
```

### Example 2: Paraphrased Query

```
Query: "List my tasks"
Hardcoded: "list" → SIMPLE ✅

Query: "Can you tell me what tasks I have?"
Hardcoded: No match → DEFAULT ❌
LLM: SIMPLE ✅ (understands intent)
```

### Example 3: Context-Dependent

```
Query: "Analyze sprint 5"
Context: User just said "I need a quick summary"
LLM: SIMPLE ✅ (considers context)

Query: "Analyze sprint 5"  
Context: User just said "I need comprehensive report for stakeholders"
LLM: COMPLEX ✅ (considers context)
```

---

## Final Recommendation

**Use LLM-based classification:**

```python
# Intelligent, not hardcoded
classification = llm.classify(query)  # ~100ms, $0.0001

# Benefits:
✅ Understands intent (not just keywords)
✅ Handles paraphrasing naturally
✅ Adapts to new query types
✅ Considers context
✅ Very fast (single LLM call)
✅ Very cheap (~$0.0001 per query)

# Cost analysis:
- 1,000 queries/day = $0.10/day = $3/month
- Saves 10x the cost by routing efficiently
```

**Implementation priority:**
1. Start with LLM classification (Solution 1)
2. Add few-shot examples if accuracy needs improvement (Solution 5)
3. Optional: Add fast heuristics for obvious cases (Solution 4)

---

## Answer to Your Question

**"How does LLM know which request is simple?"**

**A:** You DON'T hardcode it! You ask the LLM to classify:

```python
# ❌ DON'T do this (hardcoded, brittle)
if "list" in query or "show" in query:
    return "simple"

# ✅ DO this (intelligent, flexible)
classification = llm.invoke("Is this query simple or complex: {query}")
return classification  # LLM understands intent, context, nuance
```

**Cost:** ~$0.0001 per query (negligible)
**Time:** ~100ms (faster than avoiding it saves)
**Benefit:** Intelligent routing saves 10x on complex queries

**The LLM IS the intelligence - use it for classification!** 🎯


