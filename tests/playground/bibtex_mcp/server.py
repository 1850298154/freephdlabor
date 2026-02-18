"""
BibTeX MCP Server - 主入口

启动方式:
    python server.py

MCP配置 (ccswitch):
    URL: http://localhost:8000/mcp
"""

from mcp.server import FastMCP
from config import Config

# 直接导入各个模块以避免循环依赖
from tools.cache import CitationCache
from tools.search import search_and_cache, list_cached, get_paper_by_key
from tools.verify import verify_citations

# 初始化缓存（有状态，用类）
cache = CitationCache()


# 创建FastMCP服务器
mcp = FastMCP(
    name="bibtex-server",
    host=Config.HOST,
    port=Config.PORT,
    sse_path="/sse",
    streamable_http_path="/mcp"
)


# ========== MCP 工具 ===========

@mcp.tool()
def search_bibtex(query: str, limit: int = 5, cache: bool = True) -> str:
    """
    搜索论文并获取 BibTeX（同时缓存）

    Args:
        query: 搜索关键词（论文标题、作者名、主题等）
        limit: 返回结果数量（默认5）
        cache: 是否缓存到本地（默认True）

    Returns:
        JSON格式的论文列表，包含标题、BibTeX、摘要等
    """
    cache_instance = cache if cache else None
    return search_and_cache(query, limit, cache_instance)


@mcp.tool()
def list_cached_papers() -> str:
    """
    列出所有缓存的论文

    Returns:
        JSON格式的缓存论文列表
    """
    return list_cached(cache)


@mcp.tool()
def verify_citations(latex_content: str = "", bibtex_content: str = "") -> str:
    r"""
    验证LaTeX内容中的引用是否与缓存一致

    Args:
        latex_content: LaTeX文档内容（提取\cite{}引用）
        bibtex_content: .bib文件内容（验证BibTeX条目是否一致）

    Returns:
        验证结果，包括匹配和未匹配的引用
    """
    return verify_citations(latex_content, bibtex_content, cache)


@mcp.tool()
def get_cached_paper(citation_key: str) -> str:
    """
    根据引用键获取缓存的论文

    Args:
        citation_key: BibTeX引用键（如 Vaswani2017）

    Returns:
        论文的完整信息或错误信息
    """
    return get_paper_by_key(citation_key, cache)


@mcp.tool()
def clear_cache() -> str:
    """
    清空所有缓存的论文
    """
    cache.clear()
    import json
    return json.dumps({"message": "Cache cleared"}, ensure_ascii=False)


# ========== 启动服务器 ==========

def print_banner():
    """打印启动横幅"""
    print(f"""
    ╔═══════════════════════════════════════════════════════════╗
    ║           BibTeX MCP Server (Refactored)               ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  HTTP端点: http://{Config.HOST}:{Config.PORT}/mcp              ║
    ║  SSE端点:  http://{Config.HOST}:{Config.PORT}/sse              ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  可用工具:                                                ║
    ║    - search_bibtex: 搜索论文并缓存                          ║
    ║    - list_cached_papers: 列出缓存                          ║
    ║    - verify_citations: 验证引用                          ║
    ║    - get_cached_paper: 获取指定论文                        ║
    ║    - clear_cache: 清空缓存                                ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  MCP配置 (ccswitch):                                       ║
    ║    URL: http://{Config.HOST}:{Config.PORT}/mcp                 ║
    ║    缓存文件: {Config.CACHE_FILE}                                ║
    ╚═══════════════════════════════════════════════════════════╝
    """)


def main():
    """启动MCP服务器"""
    print_banner()
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
