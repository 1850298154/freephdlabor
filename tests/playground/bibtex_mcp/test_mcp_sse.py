"""
测试 MCP 服务 - 使用 SSE 流式连接
"""

import json
import requests
from urllib.parse import urlencode

MCP_URL = "http://0.0.0.0:8000/mcp"

# SSE 连接，发送 JSON-RPC 方法
url = MCP_URL + "?" + urlencode({"method": "initialize"})
headers = {
    "Accept": "application/json, text/event-stream",
}

print("=== 1. Initialize (SSE) ===")
print(f"URL: {url}")

with requests.get(url, stream=True, timeout=30) as resp:
    print(f"Status: {resp.status_code}")
    for line in resp.iter_lines(decode_unicode=True):
        if line.startswith("data:"):
            data = json.loads(line[5:])
            print(f"Init result: {data.get('result', {}).get('serverInfo', {})}")
            break

# List tools via SSE
url = MCP_URL + "?" + urlencode({"method": "tools/list"})
print(f"\n=== 2. List Tools (SSE) ===")
print(f"URL: {url}")

with requests.get(url, stream=True, timeout=30) as resp:
    print(f"Status: {resp.status_code}")
    for line in resp.iter_lines(decode_unicode=True):
        if line.startswith("data:"):
            data = json.loads(line[5:])
            if "result" in data:
                tools = data["result"].get("tools", [])
                print(f"Found {len(tools)} tools:")
                for t in tools:
                    print(f"  - {t['name']}: {t['description'][:50]}")
            break

# Call search_bibtex via SSE
url = MCP_URL + "?" + urlencode({
    "method": "tools/call",
    "name": "search_bibtex",
    "arguments": json.dumps({"query": "attention", "limit": 2})
})
print(f"\n=== 3. Call search_bibtex (SSE) ===")
print(f"URL: {url}")

with requests.get(url, stream=True, timeout=60) as resp:
    print(f"Status: {resp.status_code}")
    for line in resp.iter_lines(decode_unicode=True):
        if line.startswith("data:"):
            data = json.loads(line[5:])
            if "result" in data:
                result = json.loads(data["result"])
                papers = result.get("papers", [])
                print(f"Success! Got {len(papers)} papers:")
                for p in papers:
                    print(f"  - {p['title']}")
            elif "error" in data:
                print(f"Error: {data['error']}")
            break
