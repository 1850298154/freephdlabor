"""
BibTeX MCP Server - 增强版

功能:
    1. 搜索论文并获取 BibTeX、标题、摘要
    2. 将引用的论文缓存到本地
    3. 验证引用是否与缓存一致

启动方式:
    python bibtex_mcp_http_server.py

MCP配置 (ccswitch):
    URL: http://localhost:8000/mcp
"""

import json
import os
from datetime import datetime
from typing import Any, Dict
from mcp.server import FastMCP
import requests
from ratelimit import limits, sleep_and_retry
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from requests.exceptions import RequestException
from dotenv import load_dotenv

load_dotenv()

# ========== 配置 ==========
CACHE_FILE = ".bibtex_cache.json"  # 本地缓存文件


# ========== 缓存管理 ==========
class CitationCache:
    """论文引用缓存管理器"""

    def __init__(self, cache_file: str):
        self.cache_file = cache_file
        self.cache = self._load()

    def _load(self) -> Dict:
        """加载缓存"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save(self):
        """保存缓存"""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def add(self, paper: Dict):
        """添加论文到缓存"""
        # 提取BibTeX中的引用键
        bibtex = paper.get('bibtex', '')
        citation_key = self._extract_citation_key(bibtex)

        if not citation_key:
            citation_key = f"unknown_{datetime.now().timestamp()}"

        self.cache[citation_key] = {
            "title": paper.get('title', ''),
            "bibtex": bibtex,
            "abstract": paper.get('abstract', ''),
            "authors": paper.get('authors', []),
            "venue": paper.get('venue', ''),
            "year": paper.get('year', ''),
            "url": paper.get('url', ''),
            "cached_at": datetime.now().isoformat()
        }
        self._save()
        return citation_key

    def get(self, citation_key: str) -> Dict:
        """根据引用键获取论文"""
        return self.cache.get(citation_key)

    def list_all(self) -> Dict:
        """列出所有缓存的论文"""
        return self.cache

    def _extract_citation_key(self, bibtex: str) -> str:
        """从BibTeX中提取引用键"""
        import re
        match = re.search(r'@\w+\{([^,]+),', bibtex)
        return match.group(1) if match else ""

    def verify(self, bibtex_content: str) -> Dict:
        """
        验证BibTeX内容是否与缓存一致

        Args:
            bibtex_content: 客户端插入的BibTeX内容

        Returns:
            {
                "valid": bool,
                "citation_keys": [...],
                "mismatched": [...],  # 不匹配或缺失的引用键
                "matched": [...]       # 匹配的引用键
            }
        """
        # 提取BibTeX内容中的所有引用键
        citation_keys = self._extract_all_citation_keys(bibtex_content)

        matched = []
        mismatched = []

        for key in citation_keys:
            cached = self.get(key)
            if cached:
                # 比较BibTeX内容是否一致
                cached_bibtex = cached.get('bibtex', '')
                if key in bibtex_content:
                    # 尝试提取这篇论文的BibTeX条目进行比较
                    entry = self._extract_bibtex_entry(bibtex_content, key)
                    if entry:
                        if self._bibtex_similar(entry, cached_bibtex):
                            matched.append({
                                "key": key,
                                "title": cached.get('title'),
                                "status": "matched"
                            })
                        else:
                            mismatched.append({
                                "key": key,
                                "title": cached.get('title'),
                                "status": "modified",
                                "cached": cached_bibtex[:100] + "...",
                                "provided": entry[:100] + "..."
                            })
                    else:
                        matched.append({
                            "key": key,
                            "title": cached.get('title'),
                            "status": "not_in_bib_file"  # 只用了引用键，没在.bib文件中
                        })
                else:
                    matched.append({
                        "key": key,
                        "title": cached.get('title'),
                        "status": "cite_only"  # 只用了\cite{key}，没在.bib文件中
                    })
            else:
                mismatched.append({
                    "key": key,
                    "status": "not_cached",
                    "message": "此引用不在缓存中"
                })

        return {
            "valid": len(mismatched) == 0,
            "total": len(citation_keys),
            "matched_count": len(matched),
            "mismatched_count": len(mismatched),
            "matched": matched,
            "mismatched": mismatched
        }

    def _extract_all_citation_keys(self, content: str) -> list:
        """从LaTeX内容中提取所有引用键"""
        import re
        # 匹配 \cite{...} 或 \citep{...} 等
        patterns = [
            r'\\cite\{([^}]+)\}',
            r'\\citep\{([^}]+)\}',
            r'\\citet\{([^}]+)\}',
            r'\\citeauthor\{([^}]+)\}',
            r'\\citeyear\{([^}]+)\}'
        ]
        keys = []
        for pattern in patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                # 处理多个引用，如 \cite{key1,key2}
                keys.extend([k.strip() for k in match.split(',')])
        # 从BibTeX文件中也提取引用键
        bibtex_keys = re.findall(r'@\w+\{([^,]+),', content)
        keys.extend(bibtex_keys)
        return list(set(k.strip() for k in keys if k.strip()))

    def _extract_bibtex_entry(self, content: str, citation_key: str) -> str:
        """从BibTeX内容中提取指定键的完整条目"""
        import re
        pattern = rf'@\w+\{{{re.escape(citation_key)},.*?\n\}}'
        match = re.search(pattern, content, re.DOTALL)
        return match.group(0) if match else ""

    def _bibtex_similar(self, bibtex1: str, bibtex2: str) -> bool:
        """比较两个BibTeX是否相似（忽略空格和大小写）"""
        import re
        # 归一化：移除多余空格、换行，转小写
        normalize = lambda s: re.sub(r'\s+', ' ', s).strip().lower()
        return normalize(bibtex1) == normalize(bibtex2)


# 初始化
cache = CitationCache(CACHE_FILE)

# 创建FastMCP服务器
mcp = FastMCP(
    name="bibtex-server",
    host="0.0.0.0",
    port=8000,
    sse_path="/sse",
    streamable_http_path="/mcp"
)


# ========== API限流 + 重试 ==========
@sleep_and_retry
@limits(calls=5, period=60)
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type((RequestException, requests.HTTPError))
)
def fetch_papers_from_api(query: str, limit: int = 5) -> list[Dict]:
    """从Semantic Scholar获取论文信息"""
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    headers = {}

    S2_API_KEY = os.getenv("S2_API_KEY")
    if S2_API_KEY:
        headers["X-API-KEY"] = S2_API_KEY

    params = {
        "query": query,
        "limit": limit,
        "fields": "title,citationStyles,abstract,authors,venue,year,url,externalIds"
    }

    resp = requests.get(url, params=params, timeout=30, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    papers = []
    for item in data.get("data", []):
        bibtex = item.get("citationStyles", {}).get("bibtex", "")
        papers.append({
            "title": item.get("title", ""),
            "abstract": item.get("abstract", ""),
            "authors": [a.get("name", "") for a in item.get("authors", [])],
            "venue": item.get("venue", ""),
            "year": item.get("year", ""),
            "url": item.get("url", ""),
            "arxiv_id": item.get("externalIds", {}).get("ArXiv", ""),
            "bibtex": bibtex
        })

    return papers


# ========== MCP工具 ==========
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
    papers = fetch_papers_from_api(query, limit)

    # 缓存并构建结果
    results = []
    for paper in papers:
        citation_key = None
        if cache:
            citation_key = cache.add(paper)

        results.append({
            "citation_key": citation_key,
            "title": paper["title"],
            "bibtex": paper["bibtex"],
            "abstract": paper["abstract"],
            "authors": paper["authors"],
            "venue": paper["venue"],
            "year": paper["year"],
            "url": paper["url"]
        })

    return json.dumps({
        "query": query,
        "count": len(results),
        "papers": results,
        "cached": cache
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def list_cached_papers() -> str:
    """
    列出所有缓存的论文

    Returns:
        JSON格式的缓存论文列表
    """
    all_papers = cache.list_all()
    return json.dumps({
        "total": len(all_papers),
        "papers": all_papers
    }, ensure_ascii=False, indent=2)


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
    # 合并内容进行分析
    content = latex_content + "\n" + bibtex_content
    result = cache.verify(content)

    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def get_cached_paper(citation_key: str) -> str:
    """
    根据引用键获取缓存的论文

    Args:
        citation_key: BibTeX引用键（如 Vaswani2017）

    Returns:
        论文的完整信息或错误信息
    """
    paper = cache.get(citation_key)
    if paper:
        return json.dumps(paper, ensure_ascii=False, indent=2)
    else:
        return json.dumps({
            "error": f"Citation key '{citation_key}' not found in cache",
            "suggestion": "Use search_bibtex to find and cache papers first"
        }, ensure_ascii=False)


@mcp.tool()
def clear_cache() -> str:
    """
    清空所有缓存的论文
    """
    cache.cache = {}
    cache._save()
    return json.dumps({"message": "Cache cleared"}, ensure_ascii=False)


# ========== 启动服务器 ==========
if __name__ == "__main__":
    print(f"""
    ╔═══════════════════════════════════════════════════════════╗
    ║           BibTeX MCP Server (Enhanced)                    ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  HTTP端点: http://0.0.0.0:8000/mcp                      ║
    ║  SSE端点:  http://0.0.0.0:8000/sse                      ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  可用工具:                                                ║
    ║    - search_bibtex: 搜索论文并缓存                          ║
    ║    - list_cached_papers: 列出缓存                          ║
    ║    - verify_citations: 验证引用                          ║
    ║    - get_cached_paper: 获取指定论文                        ║
    ║    - clear_cache: 清空缓存                                ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  MCP配置 (ccswitch):                                       ║
    ║    URL: http://localhost:8000/mcp                         ║
    ║    缓存文件: {CACHE_FILE}                                ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))

    mcp.host = host
    mcp.port = port

    mcp.run(transport="streamable-http")
