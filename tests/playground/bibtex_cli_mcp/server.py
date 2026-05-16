"""
BibTeX MCP Server - CLI 版本（stdio 传输）

启动方式：直接运行此文件
MCP 配置示例：
{
  "args": ["D:\\zyt\\git_ln\\freephdlabor\\tests\\playground\\bibtex_cli_mcp\\server.py"],
  "command": "python",
  "env": {
    "S2_API_KEY": "s2k-Fa0SA2LjDGWZ1iYaHgpwp7GqUQHrHkmv05EWFh9v"
  },
  "type": "stdio"
}
"""

import os
import json
import requests
from pathlib import Path
from mcp.server import FastMCP
from ratelimit import limits, sleep_and_retry
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from requests.exceptions import RequestException

# 配置
API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
API_KEY = os.getenv("S2_API_KEY", "")
CACHE_FILE = Path(__file__).parent / ".bibtex.json"

# 初始化 MCP 服务器
mcp = FastMCP(name="bibtex-cli-server")


# ==================== 缓存管理 ====================
class Cache:
    """简单的 JSON 文件缓存"""
    _instance = None
    _data = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        """加载缓存"""
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
            except:
                self._data = {}

    def _save(self):
        """保存缓存"""
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def get(self, key: str) -> dict | None:
        """获取缓存"""
        return self._data.get(key)

    def add(self, bibtex: str, paper_info: dict):
        """添加缓存"""
        # 从 BibTeX 中提取 key
        lines = bibtex.strip().split('\n')
        if lines:
            first_line = lines[0]
            if '{' in first_line:
                key = first_line.split('{')[1].split(',')[0].strip()
                if key:
                    self._data[key] = paper_info
                    self._save()


# ==================== API 调用 ====================
@sleep_and_retry
@limits(calls=1, period=1)
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type((RequestException, requests.HTTPError))
)
def search_papers(query: str, limit: int = 5) -> list[dict]:
    """搜索论文"""
    headers = {}
    if API_KEY:
        headers["X-API-KEY"] = API_KEY

    params = {
        "query": query,
        "limit": limit,
        "fields": "title,citationStyles,abstract,authors,venue,year,url"
    }

    resp = requests.get(API_URL, params=params, timeout=30, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    papers = []
    for item in data.get("data", []):
        bibtex = item.get("citationStyles", {}).get("bibtex", "")
        if bibtex:
            papers.append({
                "title": item.get("title", ""),
                "abstract": item.get("abstract", ""),
                "authors": [a.get("name", "") for a in item.get("authors", [])],
                "venue": item.get("venue", ""),
                "year": item.get("year", ""),
                "url": item.get("url", ""),
                "bibtex": bibtex
            })

    return papers


# ==================== MCP 工具 ====================
@mcp.tool()
def search_bibtex_and_abstract(query: str, limit: int = 5) -> str:
    """
    搜索论文并获取BibTeX

    搜索时会自动缓存论文，后续验证时无需再次请求

    Args:
        query: 搜索关键词
        limit: 返回数量（默认5）
    """
    cache = Cache()
    papers = search_papers(query, limit)

    # 缓存结果
    for paper in papers:
        cache.add(paper["bibtex"], paper)

    # 格式化输出
    results = [{
        "title": p["title"],
        "bibtex": p["bibtex"],
        "abstract": p["abstract"],
        "authors": p["authors"],
        "venue": p["venue"],
        "year": p["year"],
        "url": p["url"]
    } for p in papers]

    return json.dumps({
        "query": query,
        "count": len(results),
        "papers": results
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def verify_citations_with_mismatches(bibtex_content: str) -> str:
    """
    验证BibTeX引用

    传入完整的 .bib 文件内容，返回每条引用的验证结果

    Args:
        bibtex_content: 完整的 .bib 文件内容
    """
    import re

    cache = Cache()

    # 提取所有引用键
    pattern = r'@\w+\{([^,]+),'
    keys = re.findall(pattern, bibtex_content)

    matched = []
    mismatched = []
    not_found = []

    for key in keys:
        cached = cache.get(key)

        if cached is None:
            not_found.append({
                "key": key,
                "reason": "未在缓存中找到"
            })
        else:
            # 提取输入 BibTeX 中的标题
            title_match = re.search(r'title\s*=\s*[{"]([^}"]+)[}"]', bibtex_content)
            input_title = title_match.group(1) if title_match else ""

            # 简单比较标题
            if input_title.strip().lower() in cached.get("title", "").lower():
                matched.append({
                    "key": key,
                    "title": cached["title"],
                    "bibtex": cached["bibtex"]
                })
            else:
                mismatched.append({
                    "key": key,
                    "title": cached["title"],
                    "reason": "BibTeX内容不一致",
                    "cached_bibtex": cached["bibtex"]
                })

    return json.dumps({
        "valid": len(mismatched) == 0 and len(not_found) == 0,
        "total": len(keys),
        "matched_count": len(matched),
        "mismatched_count": len(mismatched),
        "not_found_count": len(not_found),
        "matched": matched,
        "mismatched": mismatched,
        "not_found": not_found
    }, ensure_ascii=False, indent=2)


# ==================== 主函数 ====================
if __name__ == "__main__":
    print(f"启动 BibTeX MCP Server (CLI 模式)", file=__import__('sys').stderr)
    print(f"API Key: {'已设置' if API_KEY else '未设置'}", file=__import__('sys').stderr)
    print(f"缓存文件: {CACHE_FILE}", file=__import__('sys').stderr)
    mcp.run(transport="stdio")
