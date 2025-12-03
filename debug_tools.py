
import asyncio
from core.session import MultiMCP
import yaml
import os
import json

async def main():
    # Load config to get servers
    with open("config/profiles.yaml", "r") as f:
        profile = yaml.safe_load(f)
        mcp_servers_list = profile.get("mcp_servers", [])
        mcp_servers = {server["id"]: server for server in mcp_servers_list}

    multi_mcp = MultiMCP(server_configs=list(mcp_servers.values()))
    await multi_mcp.initialize()

    print("\n--- Testing search_stored_documents ---")
    try:
        result = await multi_mcp.call_tool('search_stored_documents', {"input": {"query": "test"}})
        print(f"Raw Result: {result}")
        if result.content and result.content[0].text:
            try:
                parsed = json.loads(result.content[0].text)
                print(f"JSON Keys: {list(parsed.keys())}")
                print(f"JSON Dump: {json.dumps(parsed, indent=2)}")
            except:
                print("Not JSON")
    except Exception as e:
        print(f"Error: {e}")

    print("\n--- Testing duckduckgo_search_results ---")
    try:
        result = await multi_mcp.call_tool('duckduckgo_search_results', {"input": {"query": "test", "max_results": 2}})
        print(f"Raw Result: {result}")
        if result.content and result.content[0].text:
            try:
                parsed = json.loads(result.content[0].text)
                print(f"JSON Keys: {list(parsed.keys())}")
                print(f"JSON Dump: {json.dumps(parsed, indent=2)}")
            except:
                print("Not JSON")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
