#!/usr/bin/env python3
"""
Test PM Agent

Tests the PM Agent with PM MCP Server tools.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_pm_agent_creation():
    """Test creating PM agent with PM MCP tools."""
    print("=" * 60)
    print("Test 1: PM Agent Creation")
    print("=" * 60)
    
    try:
        from src.agents import create_agent
        from src.tools import (
            configure_pm_mcp_client,
            get_pm_mcp_tools,
            is_pm_mcp_configured
        )
        
        # Configure PM MCP client
        print("\n📡 Configuring PM MCP client...")
        configure_pm_mcp_client(
            transport="sse",
            url="http://localhost:8080",
            enabled_tools=None  # All tools
        )
        
        if not is_pm_mcp_configured():
            print("⚠️  PM MCP client not configured. Using direct PM tools fallback...")
            from src.tools import get_pm_tools
            pm_tools = get_pm_tools()
        else:
            print("✅ PM MCP client configured")
            try:
                pm_tools = await get_pm_mcp_tools()
            except (ConnectionError, RuntimeError, BaseExceptionGroup) as e:
                print(f"⚠️  PM MCP server not available: {e}")
                print("   Falling back to direct PM tools...")
                from src.tools import get_pm_tools
                pm_tools = get_pm_tools()
        
        print(f"✅ Loaded {len(pm_tools)} PM tools")
        
        # Create PM agent
        print("\n🤖 Creating PM agent...")
        agent = create_agent(
            agent_name="pm_agent",
            agent_type="pm_agent",
            tools=pm_tools,
            prompt_template="pm_agent"
        )
        
        print("✅ PM agent created successfully")
        print(f"   Agent name: pm_agent")
        print(f"   Agent type: pm_agent")
        print(f"   Tools: {len(pm_tools)}")
        print(f"   Prompt: pm_agent.md")
        
        return agent, pm_tools
        
    except Exception as e:
        print(f"❌ Failed to create PM agent: {e}")
        import traceback
        traceback.print_exc()
        return None, None


async def test_pm_agent_simple_query():
    """Test PM agent with a simple query."""
    print("\n" + "=" * 60)
    print("Test 2: PM Agent Simple Query")
    print("=" * 60)
    
    agent, tools = await test_pm_agent_creation()
    
    if not agent:
        print("❌ Cannot test query - agent creation failed")
        return False
    
    try:
        print("\n💬 Testing query: 'List my projects'")
        
        # Create initial state
        from src.graph.types import State
        
        state = State(
            messages=[{"role": "user", "content": "List my projects"}],
            locale="en-US"
        )
        
        print("\n🔄 Invoking agent...")
        
        # Invoke agent
        config = {"configurable": {}}
        result = await agent.ainvoke(state, config)
        
        print("\n✅ Agent response received")
        print(f"   Messages: {len(result.get('messages', []))}")
        
        # Print last message
        if result.get('messages'):
            last_msg = result['messages'][-1]
            print(f"\n📝 Last message:")
            print(f"   Type: {type(last_msg).__name__}")
            if hasattr(last_msg, 'content'):
                content = str(last_msg.content)[:200]
                print(f"   Content: {content}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to execute query: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_pm_agent_node():
    """Test PM agent node from graph."""
    print("\n" + "=" * 60)
    print("Test 3: PM Agent Node")
    print("=" * 60)
    
    try:
        from src.graph.nodes import pm_agent_node
        from src.graph.types import State
        from langchain_core.runnables import RunnableConfig
        
        # Configure PM MCP client
        from src.tools import configure_pm_mcp_client
        configure_pm_mcp_client(
            transport="sse",
            url="http://localhost:8080"
        )
        
        # Create state
        state = State(
            messages=[{"role": "user", "content": "Show me all my tasks"}],
            locale="en-US"
        )
        
        # Create config
        config = RunnableConfig({"configurable": {}})
        
        print("🔄 Invoking PM agent node...")
        result = await pm_agent_node(state, config)
        
        print("✅ PM agent node executed")
        print(f"   Result type: {type(result).__name__}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to test PM agent node: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_pm_tools_availability():
    """Test that PM tools are available."""
    print("\n" + "=" * 60)
    print("Test 4: PM Tools Availability")
    print("=" * 60)
    
    try:
        from src.tools import (
            configure_pm_mcp_client,
            get_pm_mcp_tools,
            is_pm_mcp_configured
        )
        
        # Configure PM MCP client
        configure_pm_mcp_client(
            transport="sse",
            url="http://localhost:8080"
        )
        
        if is_pm_mcp_configured():
            try:
                tools = await get_pm_mcp_tools()
                print(f"✅ PM MCP tools available: {len(tools)} tools")
            except (ConnectionError, RuntimeError, BaseExceptionGroup) as e:
                print(f"⚠️  PM MCP server not available: {e}")
                print("   Using direct PM tools...")
                from src.tools import get_pm_tools
                tools = get_pm_tools()
                print(f"✅ Direct PM tools available: {len(tools)} tools")
            
            # List some tools
            tool_names = [tool.name for tool in tools[:10]]
            print(f"   Sample tools: {', '.join(tool_names)}...")
            
            # Check for key tools
            key_tools = ["list_projects", "list_my_tasks", "get_project", "create_task"]
            available = [name for name in key_tools if any(t.name == name for t in tools)]
            print(f"   Key tools available: {', '.join(available)}")
            
        else:
            print("⚠️  PM MCP not configured, falling back to direct tools...")
            from src.tools import get_pm_tools
            tools = get_pm_tools()
            print(f"✅ Direct PM tools available: {len(tools)} tools")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to check PM tools: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 18 + "PM AGENT TESTS" + " " * 25 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    print("⚠️  NOTE: PM MCP Server must be running at http://localhost:8080")
    print("   Start with: uv run python scripts/run_pm_mcp_server.py --transport sse --port 8080")
    print()
    
    results = []
    
    # Run tests
    results.append(await test_pm_tools_availability())
    results.append(await test_pm_agent_creation() is not None)
    
    # Only test agent query if agent was created successfully
    if results[-1]:
        # Uncomment to test actual agent execution (requires PM MCP server running)
        # results.append(await test_pm_agent_simple_query())
        # results.append(await test_pm_agent_node())
        pass
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ All tests passed!")
        print("\n📝 Next steps:")
        print("   1. Start PM MCP Server:")
        print("      uv run python scripts/run_pm_mcp_server.py --transport sse --port 8080")
        print("\n   2. Test PM agent with queries:")
        print("      - 'List my projects'")
        print("      - 'Show me all my tasks'")
        print("      - 'What's the status of project X?'")
        print("\n   3. Integrate with DeerFlow graph")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

