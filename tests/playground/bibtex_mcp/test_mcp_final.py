"""
测试 MCP 服务 - 正确使用 session ID
"""

import json
import requests
import sys
import io

# Fix UTF-8 encoding on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

MCP_URL = "http://0.0.0.0:8000/mcp"

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}

# 1. Initialize and get session ID
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

# Extract session ID from response header
session_id = init_resp.headers.get("Mcp-Session-Id")
print(f"Session ID: {session_id}")

# 2. List tools using session ID
print("\n=== 2. List Tools ===")
session_headers = headers.copy()
if session_id:
    session_headers["Mcp-Session-Id"] = session_id

tools_resp = requests.post(
    MCP_URL,
    json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    headers=session_headers,
    timeout=10
)
print(f"Status: {tools_resp.status_code}")

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
            break
else:
    print(f"Error: {tools_resp.text[:200]}")

# 3. Call search_bibtex_and_abstract
print("\n=== 3. Call search_bibtex_and_abstract ===")
search_resp = requests.post(
    MCP_URL,
    json={
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "search_bibtex_and_abstract",
            "arguments": {"query": "attention", "limit": 2}
        }
    },
    headers=session_headers,
    timeout=60
)
print(f"Status: {search_resp.status_code}")

if search_resp.status_code == 200:
    lines = search_resp.text.split('\n')
    for line in lines:
        if line.startswith("data:"):
            data = json.loads(line[5:])
            if "result" in data:
                # result might be dict or JSON string
                result_data = data["result"]
                if isinstance(result_data, str):
                    result = json.loads(result_data)
                else:
                    result = result_data
                papers = result.get("papers", [])
                print(f"\nSuccess! Got {len(papers)} papers:")
                for p in papers:
                    print(f"  - {p['title']}")
                    print(f"    BibTeX: {p['bibtex'][:80]}...")
            elif "error" in data:
                print(f"Error: {data['error']}")
            break
else:
    print(f"Error: {search_resp.text[:200]}")

# 4. Call verify_citations_with_mismatches
print("\n=== 4. Call verify_citations_with_mismatches ===")
test_bibtex = """@Article{Vaswani2017AttentionIA, title = {Attention Is All You Need}, author = {Ashish Vaswani}, year = {2017}}"""
verify_resp = requests.post(
    MCP_URL,
    json={
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "verify_citations_with_mismatches",
            "arguments": {"bibtex_content": test_bibtex}
        }
    },
    headers=session_headers,
    timeout=10
)
print(f"Status: {verify_resp.status_code}")

if verify_resp.status_code == 200:
    lines = verify_resp.text.split('\n')
    for line in lines:
        if line.startswith("data:"):
            data = json.loads(line[5:])
            if "result" in data:
                # result might be dict or JSON string
                result_data = data["result"]
                if isinstance(result_data, str):
                    result = json.loads(result_data)
                else:
                    result = result_data
                print(f"\nVerification result:")
                print(f"  Valid: {result.get('valid')}")
                print(f"  Matched: {result.get('matched_count')}/{result.get('total')}")
            elif "error" in data:
                print(f"Error: {data['error']}")
            break
else:
    print(f"Error: {verify_resp.text[:200]}")
