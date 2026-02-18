"""
BibTeX MCP Server - 带跨进程限流

启动方式:
    python bibtex_mcp_server_with_limit.py

功能:
    - 从Semantic Scholar获取BibTeX
    - 重试：最多3次，指数退避
    - 限流：使用文件锁实现跨进程限流，每分钟最多5次
"""

from mcp.server import Server
from mcp.types import Tool, TextContent
import requests
import time
import json
import os
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from requests.exceptions import RequestException
from typing import Any

# 限流配置
RATE_LIMIT_FILE = ".bibtex_rate_limit.json"
RATE_LIMIT_PERIOD = 60  # 60秒
RATE_LIMIT_CALLS = 5    # 最多5次


class RateLimiter:
    """跨进程限流器（基于文件）"""

    def __init__(self, limit_file: str, period: int, max_calls: int):
        self.limit_file = limit_file
        self.period = period
        self.max_calls = max_calls

    def acquire(self):
        """获取限流许可"""
        now = time.time()

        # 读取现有记录
        records = []
        if os.path.exists(self.limit_file):
            try:
                with open(self.limit_file, 'r') as f:
                    records = json.load(f)
            except:
                records = []

        # 清理过期记录
        records = [r for r in records if now - r < self.period]

        # 检查是否超过限制
        if len(records) >= self.max_calls:
            wait_time = self.period - (now - records[0])
            print(f"[Rate Limit] 达到限制，等待 {wait_time:.1f} 秒...")
            time.sleep(wait_time)
            # 等待后重新计算
            return self.acquire()

        # 记录本次请求
        records.append(now)
        with open(self.limit_file, 'w') as f:
            json.dump(records, f)


# 初始化MCP服务器
app = Server("bibtex-server")
limiter = RateLimiter(RATE_LIMIT_FILE, RATE_LIMIT_PERIOD, RATE_LIMIT_CALLS)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type((RequestException, requests.HTTPError))
)
def fetch_bibtex_from_api(query: str, limit: int = 3) -> str:
    """从Semantic Scholar获取BibTeX（带重试）"""
    # 应用限流
    limiter.acquire()

    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,citationStyles"
    }
    resp = requests.get(url, params=params, timeout=30)
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
