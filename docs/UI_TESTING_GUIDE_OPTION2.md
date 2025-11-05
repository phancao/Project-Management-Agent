# UI Testing Guide - Option 2 Implementation

## 🎯 Testing Option 2 in the Web UI

This guide helps you test the Option 2 implementation (Route Everything to DeerFlow) through the web UI.

---

## 🚀 Starting the Servers

### Option 1: Use Bootstrap Script (Recommended)

```bash
# Start both backend and frontend in development mode
./bootstrap.sh -d
```

This will start:
- **Backend API**: http://localhost:8000
- **Web UI**: http://localhost:3000

### Option 2: Start Separately

**Backend Server**:
```bash
uv run server.py --reload
```

**Frontend (in another terminal)**:
```bash
cd web
pnpm dev
```

---

## 🌐 Access the UI

Once servers are running:

1. **Open Browser**: Navigate to http://localhost:3000
2. **You should see**: The DeerFlow chat interface

---

## ✅ Test Cases for Option 2

### Test 1: Simple PM Query

**What to Test**: Verify simple PM queries route through DeerFlow

**Steps**:
1. In the chat, type: `"List my tasks"`
2. Press Enter
3. **Expected**: 
   - Query goes through DeerFlow agents
   - Agents use PM tools to fetch tasks
   - Response includes task list

**Verify**:
- ✅ Query routes to DeerFlow (check backend logs)
- ✅ PM tools are called
- ✅ Response is agent-generated

---

### Test 2: Research Query

**What to Test**: Verify research queries work with DeerFlow

**Steps**:
1. In the chat, type: `"Research sprint planning best practices"`
2. Press Enter
3. **Expected**:
   - Query routes to DeerFlow
   - Agents perform web research
   - Response includes research findings

**Verify**:
- ✅ Research is performed
- ✅ Multiple sources are consulted
- ✅ Comprehensive response

---

### Test 3: Mixed Query (PM + Research)

**What to Test**: Verify combined PM and research queries

**Steps**:
1. In the chat, type: `"Analyze our sprint velocity and compare with best practices"`
2. Press Enter
3. **Expected**:
   - Agents query PM data (sprints, tasks)
   - Agents research best practices
   - Agents combine and analyze results
   - Response includes analysis

**Verify**:
- ✅ PM tools are called
- ✅ Web research is performed
- ✅ Results are synthesized

---

### Test 4: PM Tools Integration

**What to Test**: Verify PM tools are available to agents

**Queries to Try**:
- `"Show me all projects"`
- `"What tasks are in sprint X?"`
- `"List all epics for project Y"`
- `"Who are the team members?"`

**Expected**: All queries should:
- ✅ Route through DeerFlow
- ✅ Use appropriate PM tools
- ✅ Return PM data

---

## 🔍 Monitoring Tests

### Backend Logs

Watch backend logs to verify routing:

```bash
# In terminal running server.py
# Look for:
- "Routing to DeerFlow for intent: ..."
- "PM tools called: ..."
- "Agent execution completed"
```

### Browser Console

Open browser DevTools (F12) and check:
- Network tab: API calls to `/api/chat/stream`
- Console: Any errors or warnings

---

## 📊 Expected Behavior

### All Queries Should:

1. ✅ **Route to DeerFlow**: All queries go through DeerFlow agents
2. ✅ **Use PM Tools**: PM queries use appropriate tools
3. ✅ **Agent Decision**: Agents decide which tools to use
4. ✅ **Proper Responses**: Responses are well-formatted and helpful

### Performance:

- Simple queries: ~5-15 seconds
- Research queries: ~10-30 seconds
- Mixed queries: ~10-30 seconds

---

## 🐛 Troubleshooting

### Issue: Query doesn't respond

**Check**:
1. Backend server is running (`uv run server.py --reload`)
2. Frontend is running (`cd web && pnpm dev`)
3. API is accessible (http://localhost:8000/health)

**Solution**:
- Restart both servers
- Check console for errors

---

### Issue: PM tools not working

**Check**:
1. PM provider is configured (OpenProject, JIRA, or ClickUp)
2. API keys are set in `.env`
3. PM handler is initialized (check logs)

**Solution**:
- Verify PM provider configuration
- Check API keys are correct
- Restart backend server

---

### Issue: Queries not routing to DeerFlow

**Check**:
1. DeerFlow workflow is available (check logs)
2. Routing logic is correct (check `flow_manager.py`)

**Solution**:
- Verify dependencies: `uv sync`
- Check that `run_deerflow_workflow` is not None
- Review routing code changes

---

## ✅ Success Criteria

Your Option 2 implementation is working if:

1. ✅ **All queries route to DeerFlow** (visible in logs)
2. ✅ **PM tools are called** (visible in logs)
3. ✅ **Responses are generated** (visible in UI)
4. ✅ **No errors** (check console and logs)
5. ✅ **Performance is acceptable** (queries complete in reasonable time)

---

## 🎯 Quick Test Checklist

- [ ] Backend server running on port 8000
- [ ] Frontend running on port 3000
- [ ] UI loads at http://localhost:3000
- [ ] Simple PM query works
- [ ] Research query works
- [ ] Mixed query works
- [ ] PM tools are called (check logs)
- [ ] All queries route to DeerFlow (check logs)

---

## 📝 Notes

- **Development Mode**: Use `./bootstrap.sh -d` for auto-reload
- **Logs**: Watch backend logs to see routing and tool calls
- **API Docs**: http://localhost:8000/docs for API testing
- **Health Check**: http://localhost:8000/health

---

**Ready to Test!** 🚀

Open http://localhost:3000 and start testing Option 2 implementation!
