# Evaluator Workflow Implementation

## Problem Statement

The previous workflow stopped immediately after generating a report, without checking if the report actually satisfied the user's request. This caused issues like:

- User asks: "Analyze this project"
- System gathers project data (name, description, status)
- System generates report listing the data
- System stops ❌

**Expected behavior:** The system should recognize that "analyze" requires more than just data listing - it needs metrics, insights, and recommendations (burndown, velocity, allocation, etc.).

## Solution: Evaluator Node

Added a new `evaluator` node that acts as a quality gate between the reporter and the end of the workflow.

### Workflow Flow

**Old Flow:**
```
planner → research_team → reporter → END
```

**New Flow:**
```
planner → research_team → reporter → evaluator → (END or back to planner)
                                                    ↑                    |
                                                    |____________________|
                                                    (if report incomplete)
```

### How It Works

1. **Reporter generates initial report** from gathered data
2. **Evaluator assesses the report** by checking:
   - Does it answer the user's original question?
   - For "analyze" queries: Does it include analysis, metrics, insights?
   - For "list" queries: Is the data complete and properly formatted?
3. **Decision:**
   - ✅ **SATISFIED**: Report is complete → Route to `END`
   - ❌ **NOT SATISFIED**: Report needs more work → Route to `planner` with new instructions

### Example: "Analyze this project"

**Iteration 1:**
- Planner: "Gather project data"
- Research: Retrieves project name, description, status
- Reporter: "Here's the project information..."
- Evaluator: ❌ "This only lists data, no analysis. Need: burndown, velocity, allocation"
- → Creates new plan

**Iteration 2:**
- Planner: "Analyze project metrics"
- Research: Calculates burndown, velocity, team allocation
- Reporter: "Project Analysis: Burndown shows 20% completion, velocity is 15 points/sprint..."
- Evaluator: ✅ "Complete analysis with metrics and insights"
- → END

### Safety Features

- **Max 3 iterations**: Prevents infinite loops
- **Graceful fallback**: If evaluator fails to parse, assumes complete and ends
- **Clear logging**: Each evaluation decision is logged for debugging

## Files Changed

1. **src/prompts/evaluator.md** (NEW)
   - Prompt template for the evaluator agent
   - Defines evaluation criteria for different query types
   - Provides examples of satisfied vs. not satisfied reports

2. **src/graph/nodes.py**
   - Added `evaluator_node()` function
   - Evaluates report quality and routes accordingly
   - Handles JSON parsing and error cases

3. **src/graph/builder.py**
   - Imported `evaluator_node`
   - Added evaluator to the workflow graph
   - Changed routing: `reporter → evaluator` instead of `reporter → END`

4. **src/config/agents.py**
   - Added `"evaluator": "basic"` to `AGENT_LLM_MAP`

## Testing

To test the new workflow:

1. **Simple data query** (should complete in 1 iteration):
   ```
   User: "List my tasks"
   → Gathers tasks → Reports tasks → Evaluator: ✅ Complete → END
   ```

2. **Analysis query** (should take 2+ iterations):
   ```
   User: "Analyze this project"
   → Iteration 1: Gathers data → Reports data → Evaluator: ❌ Need analysis
   → Iteration 2: Analyzes metrics → Reports analysis → Evaluator: ✅ Complete → END
   ```

## Benefits

1. **Smarter responses**: System understands the difference between "list" and "analyze"
2. **Comprehensive analysis**: For analysis queries, ensures metrics and insights are provided
3. **Self-correcting**: If initial report is insufficient, system automatically creates follow-up plan
4. **User satisfaction**: Reports now match user expectations based on their query type

## Configuration

The evaluator uses the same LLM as the planner (`basic` type). To change:

```python
# In src/config/agents.py
AGENT_LLM_MAP = {
    "evaluator": "reasoning",  # Use reasoning model for better evaluation
    ...
}
```

## Monitoring

Check logs for evaluator decisions:

```bash
docker-compose logs -f api | grep -i "evaluator"
```

Look for:
- `Evaluator assessing report quality and completeness`
- `Evaluation result: satisfied=true/false`
- `Report satisfies user request, ending workflow`
- `Report incomplete, creating new plan`
