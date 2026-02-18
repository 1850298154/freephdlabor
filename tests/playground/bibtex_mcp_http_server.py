"""
BibTeX MCP HTTP Server - 支持通过URL访问的MCP服务器

启动方式:
    python bibtex_mcp_http_server.py

服务运行在: http://localhost:8000/mcp

MCP配置 (ccswitch):
    URL: http://localhost:8000/mcp
"""

from mcp.server import FastMCP
from mcp.types import Tool, TextContent
import requests
from ratelimit import limits, sleep_and_retry
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from requests.exceptions import RequestException
import os
from dotenv import load_dotenv

load_dotenv()

# 创建FastMCP服务器（支持HTTP/SSE）
mcp = FastMCP(
    name="bibtex-server",
    host="0.0.0.0",  # 允许外部访问
    port=8000,
    sse_path="/sse",           # SSE端点
    streamable_http_path="/mcp" # HTTP JSON-RPC端点
)


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


@mcp.tool()
def get_bibtex(query: str, limit: int = 3) -> str:
    """
    从Semantic Scholar API获取论文的BibTeX引用格式

    Args:
        query: 搜索关键词（论文标题、作者名、主题等）
        limit: 返回结果数量（默认3）
    """
    return fetch_bibtex_from_api(query, limit)


if __name__ == "__main__":
    print(f"""
    ╔═══════════════════════════════════════════════════════════╗
    ║           BibTeX MCP Server (HTTP/SSE)                    ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  HTTP端点: http://0.0.0.0:8000/mcp                      ║
    ║  SSE端点:  http://0.0.0.0:8000/sse                      ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  MCP配置 (ccswitch):                                       ║
    ║    URL: http://localhost:8000/mcp                         ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    # 从环境变量读取配置（可选）
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))

    # 更新配置
    mcp.host = host
    mcp.port = port

    # 运行服务器
    mcp.run(transport="streamable-http")
