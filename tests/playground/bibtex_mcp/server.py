"""
BibTeX MCP Server - 精简版

启动: python server.py

ccswitch配置: http://localhost:8000/mcp
"""

from mcp.server import FastMCP
from config import HOST, PORT
from tools import search_bibtex, verify_citations

mcp = FastMCP(
    name="bibtex-server",
    host=HOST,
    port=PORT,
    sse_path="/sse",
    streamable_http_path="/mcp"
)


@mcp.tool()
def search_bibtex(query: str, limit: int = 5) -> str:
    """
    搜索论文并获取BibTeX

    搜索时会自动缓存论文，后续验证时无需再次请求
    """
    return tools.search_bibtex(query, limit)


@mcp.tool()
def verify_citations(bibtex_content: str) -> str:
    """
    验证BibTeX引用

    传入完整的 .bib 文件内容，返回每条引用的验证结果
    """
    return tools.verify_citations(bibtex_content)


if __name__ == "__main__":
    print(f"""
    ╔═════════════════════════════════════════════════════════╗
    ║           BibTeX MCP Server (Minimal)                    ║
    ╠═════════════════════════════════════════════════════════╣
    ║  URL: http://{HOST}:{PORT}/mcp                             ║
    ║  缓存文件: .bibtex.json                                     ║
    ╠═════════════════════════════════════════════════════════╣
    ║  工具:                                                    ║
    ║    - search_bibtex: 搜索论文（自动缓存）                ║
    ║    - verify_citations: 验证引用                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    mcp.run(transport="streamable-http")
