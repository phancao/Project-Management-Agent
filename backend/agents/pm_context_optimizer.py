"""
Context Optimizer for PM Agent

Optimizes large tool outputs using LLM to fit within context window while preserving 
information relevant to the user's query.
"""
import json
import logging
from typing import Any, Dict, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from backend.llms.llm import get_llm_by_type

logger = logging.getLogger(__name__)

class PMToolContextOptimizer:
    """
    Optimizes structured tool outputs (PM Data) for the agent's context.
    Ensures that large JSON lists are preserved (preventing item loss) while 
    minimizing token usage by stripping unnecessary fields.
    """
    
    def __init__(self, threshold_chars: int = 2000):
        self.threshold_chars = threshold_chars
        # Use basic/fast LLM for optimization to minimize latency
        self.llm = get_llm_by_type("basic") 
        
    async def optimize(self, user_query: str, tool_name: str, tool_result: str) -> str:
        """
        Optimize tool result if it exceeds threshold.
        
        Args:
            user_query: The original user request
            tool_name: Name of the tool that produced result
            tool_result: Raw string output from tool
            
        Returns:
            Optimized string (or original if optimization failed/not needed)
        """
        # 1. Chech threshold
        if len(tool_result) < self.threshold_chars:
            return tool_result
            
        try:
            # 2. Parse JSON to ensure validity (if applicable)
            # Most PM tools return JSON. If not JSON, skip optimization for now.
            try:
                data = json.loads(tool_result)
            except json.JSONDecodeError:
                return tool_result
                
            # If it's a simple small dict, skip
            if isinstance(data, dict) and len(str(data)) < self.threshold_chars:
                return tool_result

            # 🟢 NEW: Dynamic Schema Discovery (LLM-driven)
            # Instead of hardcoding fields, we ask the LLM *once* what to keep based on the query.
            if "task" in tool_name.lower() or "list_tasks" in tool_name or "sprint_report" in tool_name:
                required_fields = await self._identify_required_fields(tool_name, data, user_query)
                if required_fields:
                    filtered_result = self._apply_dynamic_filter(tool_name, data, required_fields)
                    if filtered_result:
                         filtered_len = len(filtered_result)
                         reduction = (1 - filtered_len / len(tool_result)) * 100
                         logger.info(f"[OPTIMIZER] Dynamic Filter ({tool_name}): kept {len(required_fields)} fields -> {len(tool_result)} to {filtered_len} chars ({reduction:.1f}%)")
                         return filtered_result

            # Fallback to standard optimization if not a list tool or dynamic filter failed
            logger.info(f"[OPTIMIZER] Optimizing {tool_name} result ({len(tool_result)} chars) for query: {user_query}")
            
            # 3. Construct Optimization Prompt
            system_prompt = """You are a Data Optimization AI.
Your goal is to reduce the size of the provided JSON data while PRESERVING all information relevant to the User's Query.

RULES:
1. **Filter Unnecessary Fields**: Remove fields that are clearly irrelevant to the query (e.g., internal IDs, raw URLs, dense descriptions if not asked for).
2. **Preserve Items**: If the valid data is a list (e.g., tasks, sprints), do NOT truncate the items unless explicitly told to "sample". 
   - **CRITICAL**: If there are 50 or fewer items, YOU MUST RETURN ALL OF THEM. Do not summarize or truncate the list length.
   - Use field filtering (Rule 1) to reduce size, not item dropping.
3. **Structure**: Keep the valid JSON structure.
4. **Output**: Return ONLY the minified valid JSON. No markdown formatting.
"""

            user_prompt = f"""
User Query: "{user_query}"
Tool Name: "{tool_name}"
Raw Data Length: {len(tool_result)} chars

Raw Data (truncated preview if too large):
{tool_result[:50000]} 

Optimize this data to be as compact as possible while answering the user's query.
- If the user needs to know "how many" or "list all", DO NOT remove items from the list.
- Remove voluminous text fields (description, comments) if they are not needed for the query.
"""
            
            # 4. Invoke LLM
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            optimized_result = response.content.strip()
            
            # Remove markdown code blocks if present
            if optimized_result.startswith("```json"):
                optimized_result = optimized_result[7:]
            if optimized_result.startswith("```"):
                optimized_result = optimized_result[3:]
            if optimized_result.endswith("```"):
                optimized_result = optimized_result[:-3]
                
            optimized_result = optimized_result.strip()
            
            # 5. Validation
            # Ensure it's valid JSON
            json.loads(optimized_result)
            
            reduction = (1 - len(optimized_result) / len(tool_result)) * 100
            logger.info(f"[OPTIMIZER] Success: {len(tool_result)} -> {len(optimized_result)} chars ({reduction:.1f}% reduction)")
            
            return optimized_result
            
        except Exception as e:
            logger.warning(f"[OPTIMIZER] Failed to optimize: {e}. Returning original.")
            return tool_result

    async def _identify_required_fields(self, tool_name: str, data: Any, user_query: str) -> Optional[List[str]]:
        """
        Ask LLM which fields are required for the query, using a single sample item.
        """
        try:
            sample_item = None
            if isinstance(data, list) and data:
                sample_item = data[0]
            elif isinstance(data, dict):
                # Try to find the list wrapper
                for key in ["tasks", "issues", "items", "results", "data"]:
                    if key in data and isinstance(data[key], list) and data[key]:
                        sample_item = data[key][0]
                        break
            
            if not sample_item:
                return None

            # Always include structural IDs needed for system logic
            # We add these to the LLM's output later, but hint at them here
            prompt = f"""
User Query: "{user_query}"
Tool: "{tool_name}"
Sample Item Schema:
{json.dumps(sample_item, indent=2, default=str)[:2000]}

Identify the MINIMUM set of JSON keys (fields) required from this object to answer the query.
Rules:
1. ALWAYS include identifiers like 'id', 'sprint_id', 'project_id', 'status', 'title' as they are critical for context.
2. Include descriptive fields (description, body) ONLY if the user explicitly asks for details/content.
3. Return ONLY a valid JSON list of strings. Example: ["id", "title", "status"]
"""
            messages = [
                SystemMessage(content="You are a schema optimizer. Output only JSON."),
                HumanMessage(content=prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            content = response.content.strip()
            
            # Clean markdown
            if content.startswith("```json"): content = content[7:]
            if content.startswith("```"): content = content[3:]
            if content.endswith("```"): content = content[:-3]
            
            fields = json.loads(content.strip())
            
            # Enforce critical fields that LLM might forget but system needs
            critical_fields = {
                "id", "title", "name", "status", "state", 
                "sprint_id", "project_id", 
                "story_points", "storyPoints", "story_point", "custom_fields", # Story Points robustness
                "_links", "sprint", "version"
            }
            fields = list(set(fields) | critical_fields)
            
            return fields
            
        except Exception as e:
            logger.warning(f"[OPTIMIZER] Failed to identify fields: {e}")
            return None

    def _apply_dynamic_filter(self, tool_name: str, data: Any, keep_fields: List[str]) -> Optional[str]:
        """
        Apply the identified field whitelist programmatically to the full dataset.
        """
        try:
            items = data
            wrapper_key = None
            
            if isinstance(data, dict):
                for key in ["tasks", "issues", "items", "results", "data"]:
                    if key in data and isinstance(data[key], list):
                        items = data[key]
                        wrapper_key = key
                        break
            
            if not isinstance(items, list):
                return None
                
            filtered_items = []
            keep_set = set(keep_fields)
            
            for item in items:
                if not isinstance(item, dict):
                    filtered_items.append(item)
                    continue
                    
                clean_item = {}
                for k, v in item.items():
                    # Keep requested fields OR id/name suffixes
                    if k in keep_set or k.endswith("_id") or k.endswith("_name"):
                        clean_item[k] = v
                
                # Robust Logic: Ensure sprint_id is populated (from Round 4 fix)
                # Even if LLM didn't ask for "sprint", we check nested objects if sprint_id is missing
                if "sprint_id" not in clean_item or not clean_item["sprint_id"]:
                    if isinstance(item.get("sprint"), dict):
                        clean_item["sprint_id"] = item["sprint"].get("id")
                    elif isinstance(item.get("version"), dict):
                        clean_item["sprint_id"] = item["version"].get("id")
                    elif isinstance(item.get("_links"), dict):
                        try:
                            href = item["_links"].get("version", {}).get("href", "")
                            if href:
                                clean_item["sprint_id"] = href.split("/")[-1]
                        except:
                            pass

                filtered_items.append(clean_item)
            
            # Reconstruct wrapper if needed
            if wrapper_key and isinstance(data, dict):
                new_data = data.copy()
                new_data[wrapper_key] = filtered_items
                # Strip heavy top-level fields too
                for k in list(new_data.keys()):
                    if k != wrapper_key and k not in keep_set:
                        del new_data[k]
                return json.dumps(new_data, separators=(',', ':'))
            else:
                return json.dumps(filtered_items, separators=(',', ':'))
                
        except Exception as e:
            logger.warning(f"[OPTIMIZER] Dynamic filter error: {e}")
            return None
