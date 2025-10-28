import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('.'))

async def test_graph():
    try:
        print("Testing graph import...")
        from src.graph.builder import build_graph
        print("✓ Graph import successful")
        
        print("Building graph...")
        graph = build_graph()
        print("✓ Graph built successfully")
        
        print("Testing simple state...")
        from src.graph.types import State
        state = State(messages=[{"role": "user", "content": "Hello"}])
        print("✓ State created successfully")
        
        print("Testing graph execution...")
        result = await graph.ainvoke(
            {"messages": [{"role": "user", "content": "Hello"}]},
            config={"configurable": {"thread_id": "test"}}
        )
        print(f"✓ Graph execution result: {result}")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_graph())
