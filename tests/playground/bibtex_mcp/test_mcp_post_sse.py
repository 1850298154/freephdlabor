"""
测试 MCP 服务 - POST 请求获取 SSE 响应
"""

import json
import requests

MCP_URL = "http://0.0.0.0:8000/mcp"

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}

# 1. List tools (POST)
print("=== 1. List Tools (POST) ===")
tools_resp = requests.post(
    MCP_URL,
    json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
    headers=headers,
    timeout=10
)
print(f"Status: {tools_resp.status_code}")
print(f"Response: {tools_resp.text[:500]}")

# Parse SSE response from POST
if tools_resp.status_code == 200:
    lines = tools_resp.text.split('\n')
    for line in lines:
        if line.startswith("data:"):
            data = json.loads(line[5:])
            if "result" in data:
                tools = data["result"].get("tools", [])
                print(f"\nFound {len(tools)} tools:")
                for t in tools:
                    print(f"  - {t['name']}: {t['description']}")

# 2. Call search_bibtex (POST)
print("\n=== 2. Call search_bibtex (POST) ===")
search_resp = requests.post(
    MCP_URL,
    json={
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "search_bibtex",
            "arguments": {"query": "attention", "limit": 2}
        }
    },
    headers=headers,
    timeout=60
)
print(f"Status: {search_resp.status_code}")

if search_resp.status_code == 200:
    lines = search_resp.text.split('\n')
    for line in lines:
        if line.startswith("data:"):
            data = json.loads(line[5:])
            if "result" in data:
                result = json.loads(data["result"])
                papers = result.get("papers", [])
                print(f"\nSuccess! Got {len(papers)} papers:")
                for p in papers:
                    print(f"  - {p['title']}")
            elif "error" in data:
                print(f"Error: {data['error']}")
            break
else:
    print(f"Response: {search_resp.text[:500]}")
