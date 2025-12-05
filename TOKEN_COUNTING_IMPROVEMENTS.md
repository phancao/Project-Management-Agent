# Token Counting Algorithm Improvements ✅

## Research Findings

Based on web search, the **correct way** to count tokens for OpenAI models is:

1. **Use `tiktoken.encoding_for_model(model_name)`** - This automatically selects the correct encoding for the model
2. **Avoid rough estimates** - Use actual tiktoken encoding instead of `len(text) // 4`
3. **Model-specific encoding** - Different models use different encodings:
   - GPT-3.5/4/4o: `cl100k_base`
   - GPT-3: `p50k_base`
   - `encoding_for_model()` handles this automatically

## Changes Made

### 1. Updated `context_manager.py` ✅

**Before:**
```python
# Manual mapping (error-prone)
encoding_name = "cl100k_base"
if "gpt-4" in model.lower() or "gpt-3.5" in model.lower():
    encoding_name = "cl100k_base"
elif "gpt-3" in model.lower():
    encoding_name = "p50k_base"
encoding = tiktoken.get_encoding(encoding_name)
```

**After:**
```python
# Use encoding_for_model() - automatically selects correct encoding
try:
    encoding = tiktoken.encoding_for_model(model)
except (KeyError, ValueError):
    # Fallback with proper error handling
    encoding = tiktoken.get_encoding("cl100k_base")
```

### 2. Updated ReAct Agent Token Check ✅

**Before:**
```python
# Rough estimates (inaccurate!)
output_tokens = len(output) // 4  # ❌ Rough estimate
intermediate_tokens += len(obs_str) // 4  # ❌ Rough estimate
state_tokens = sum(len(str(msg.content)) // 4 for msg in ...)  # ❌ Rough estimate
```

**After:**
```python
# Accurate tiktoken counting
import tiktoken
encoding = tiktoken.encoding_for_model(model_name_for_encoding)
output_tokens = len(encoding.encode(output))  # ✅ Accurate
intermediate_tokens += len(encoding.encode(obs_str))  # ✅ Accurate
state_tokens += len(encoding.encode(content_str))  # ✅ Accurate
```

## Benefits

1. **Accuracy**: Token counts now match OpenAI's actual counting
2. **Model-specific**: Automatically uses correct encoding for each model
3. **Reliability**: Better detection of token limit issues before they cause errors
4. **Future-proof**: Works with new models automatically (tiktoken handles it)

## Testing

When testing, you should see more accurate token counts in logs:

```
[REACT-AGENT] 🔍 DEBUG: Token check for reporter - 
  output=150, intermediate_steps=21,500, state=200, total=21,850, reporter_limit=13,927
```

The counts should now be **accurate** (not rough estimates), which means:
- Better pre-flight checks
- More reliable escalation decisions
- Fewer rate limit errors

## References

- OpenAI Token Counting Guide: https://help.openai.com/en/articles/4936856-what-are-tokens-and-how-to-count-them
- tiktoken Documentation: https://github.com/openai/tiktoken
- Best Practice: Use `tiktoken.encoding_for_model(model_name)` for model-specific encoding


