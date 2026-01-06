import httpx
import time
import asyncio
import json

async def test_endpoint(base_url, name, method, path, params=None):
    url = f"{base_url}{path}"
    print(f"\n--- Testing {name} on {base_url} ---")
    print(f"URL: {url}")
    
    start_time = time.time()
    try:
        async with httpx.AsyncClient(timeout=65.0) as client:
            response = await client.request(method, url, params=params)
            duration = time.time() - start_time
            
            print(f"Status: {response.status_code}")
            print(f"Duration: {duration:.2f}s")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Handle both list formats
                    items = []
                    if isinstance(data, dict):
                        items = data.get("items", data.get("users", []))
                    elif isinstance(data, list):
                        items = data
                        
                    count = len(items)
                    print(f"Items found: {count}")
                except Exception as e:
                    print(f"Failed to parse JSON: {e}")
            else:
                print(f"Error: {response.status_code}")
                # print(response.text[:200])
                
    except Exception as e:
        print(f"FAILED to connect: {e}")

async def main():
    print("=== TEAM MANAGEMENT API VERIFICATION ===")
    
    # 1. MCP Server (Port 8080) - Current Frontend Target
    # Check if it has convenience routes for everything
    print("\n>>> Checking MCP Server (Port 8080)")
    await test_endpoint("http://localhost:8080", "Users (Convenience)", "GET", "/users", {"limit": 5})
    await test_endpoint("http://localhost:8080", "Tasks (Direct?)", "GET", "/tasks", {"limit": 5})
    await test_endpoint("http://localhost:8080", "Tasks (API path?)", "GET", "/api/v1/tasks", {"limit": 5})

    # 2. PM Service (Port 8001) - The Real REST API
    # Check if this is where we should be pointing
    print("\n>>> Checking PM Service (Port 8001)")
    await test_endpoint("http://localhost:8001", "Users (REST)", "GET", "/api/v1/users", {"limit": 5})
    await test_endpoint("http://localhost:8001", "Tasks (REST)", "GET", "/api/v1/tasks", {"limit": 5})
    await test_endpoint("http://localhost:8001", "Time Entries (REST)", "GET", "/api/v1/time_entries", {"limit": 5})
    
    print("\n=== VERIFICATION COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(main())
