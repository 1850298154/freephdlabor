"""
测试 MCP 服务
"""

import requests
import json

MCP_URL = "http://0.0.0.0:8000/mcp"

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream"
}

# 1. Initialize
print("=== 1. Initialize ===")
init_resp = requests.post(
    MCP_URL,
    json={
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test_client", "version": "1.0"}
        }
    },
    headers=headers,
    timeout=10
)
print(f"Status: {init_resp.status_code}")
print(f"Response: {init_resp.text[:500]}")

# 2. List tools
print("\n=== 2. List Tools ===")
tools_resp = requests.post(
    MCP_URL,
    json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    headers=headers,
    timeout=10
)
print(f"Status: {tools_resp.status_code}")
print(f"Response: {tools_resp.text}")

# 3. Call search_bibtex
print("\n=== 3. Call search_bibtex ===")
search_resp = requests.post(
    MCP_URL,
    json={
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "search_bibtex",
            "arguments": {"query": "attention", "limit": 2}
        }
    },
    headers=headers,
    timeout=30
)
print(f"Status: {search_resp.status_code}")
result = json.loads(search_resp.text)
if "result" in result:
    print(f"Success! Got {len(json.loads(result['result']).get('papers', []))} papers")
    print(json.dumps(json.loads(result['result']), indent=2, ensure_ascii=False)[:500])
else:
    print(f"Error: {result}")
