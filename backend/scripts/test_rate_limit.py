import asyncio
import httpx

async def test_rate_limit():
    url = "http://localhost:8000/api/query"
    
    print("Testing Rate Limiting with mock IP: 198.51.100.1")
    
    # Simulate first query
    headers = {"X-Forwarded-For": "198.51.100.1"}
    data = {
        "query": "laptop",
        "display_currency": "USD",
        "model": "gemini-3-flash-preview"
    }
    
    print("\n--- Sending First Request ---")
    async with httpx.AsyncClient() as client:
        async with client.stream("POST", url, json=data, headers=headers) as response:
            async for line in response.aiter_lines():
                if line.startswith("event: limit_reached"):
                    print("ERROR: Limit reached on first query (should not happen)")
                    break
                if line.startswith("event: started") or line.startswith("event: complete"):
                    print("SUCCESS: First query started/completed.")
                    break
    
    print("\n--- Sending Second Request ---")
    async with httpx.AsyncClient() as client:
        async with client.stream("POST", url, json=data, headers=headers) as response:
            limit_reached = False
            async for line in response.aiter_lines():
                if line.startswith("event: limit_reached"):
                    print("SUCCESS: Second query blocked as expected.")
                    limit_reached = True
                    break
            
            if not limit_reached:
                print("ERROR: Second query was NOT blocked.")

if __name__ == "__main__":
    asyncio.run(test_rate_limit())
