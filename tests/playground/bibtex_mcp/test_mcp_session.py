"""
测试 MCP 服务 - 检查 session ID
"""

import json
import requests

MCP_URL = "http://0.0.0.0:8000/mcp"

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}

# 1. Initialize and examine response
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
print(f"Headers: {dict(init_resp.headers)}")
print(f"Response body:\n{init_resp.text[:1000]}")

# Check for cookies
print(f"\nCookies: {init_resp.cookies.get_dict()}")

# Parse SSE response
lines = init_resp.text.split('\n')
for i, line in enumerate(lines):
    if line:
        print(f"Line {i}: {line[:100]}")
        if line.startswith("data:"):
            data = json.loads(line[5:])
            print(f"  Parsed: {list(data.keys())}")
