"""
BibTeX MCP Server - 提供从Semantic Scholar API获取BibTeX的服务

启动方式:
    python bibtex_mcp_server.py

服务运行在: stdio (用于MCP客户端连接)
"""

from mcp.server import Server
from mcp.types import Tool, TextContent
import requests
from ratelimit import limits, sleep_and_retry
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from requests.exceptions import RequestException
from typing import Any
import os
from dotenv import load_dotenv
load_dotenv()

# 初始化MCP服务器
app = Server("bibtex-server")

# 限流：1分钟最多5次请求（Semantic Scholar免费限制约100/5分钟）
@sleep_and_retry
@limits(calls=5, period=60)
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type((RequestException, requests.HTTPError))
)
def fetch_bibtex_from_api(query: str, limit: int = 3) -> str:
    """从Semantic Scholar获取BibTeX（带重试和限流）"""
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    headers = {}

    S2_API_KEY = os.getenv("S2_API_KEY")
    if S2_API_KEY:
        headers["X-API-KEY"] = S2_API_KEY
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,citationStyles,abstract"
    }
    resp = requests.get(url, params=params, timeout=30, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    results = []
    for paper in data.get("data", []):
        bibtex = paper.get("citationStyles", {}).get("bibtex")
        title = paper.get("title", "Unknown")
        if bibtex:
            results.append(f"# {title}\n{bibtex}")

    return "\n\n".join(results) if results else "No results found"


@app.list_tools()
async def list_tools() -> list[Tool]:
    """列出可用工具"""
    return [
        Tool(
            name="get_bibtex",
            description="从Semantic Scholar API获取论文的BibTeX引用格式",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词（论文标题、作者名、主题等）"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回结果数量（默认3）",
                        "default": 3
                    }
                },
                "required": ["query"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """调用工具"""
    if name == "get_bibtex":
        query = arguments.get("query", "")
        limit = arguments.get("limit", 3)
        result = fetch_bibtex_from_api(query, limit)
        return [TextContent(type="text", text=result)]
    raise ValueError(f"Unknown tool: {name}")


async def main():
    """启动服务器"""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
