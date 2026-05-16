"""
BibTeX MCP Server - 完整注释版

功能：提供论文搜索和引用验证的 MCP 服务
作者：Claude
日期：2026-05-16
"""

import os
import json
import re
import requests
from pathlib import Path
from mcp.server import FastMCP
from rate_limiter import FileQueueRateLimiter


# ==================== 配置 ====================

# Semantic Scholar API 地址
API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

# API 密钥（从环境变量读取，如果没有则为空）
API_KEY = os.getenv("S2_API_KEY", "")

# 缓存文件路径（存储已搜索的论文）
CACHE_FILE = Path(__file__).parent / ".bibtex.json"

# 队列文件路径（管理请求限流）
QUEUE_FILE = Path(__file__).parent / "request_queue.json"

# 初始化限流器（每秒一次请求）
rate_limiter = FileQueueRateLimiter(str(QUEUE_FILE), min_interval=1.0)

# 初始化 MCP 服务器
mcp = FastMCP(name="bibtex-cli-server")


# ==================== 缓存管理 ====================

class Cache:
    """
    简单的JSON文件缓存

    作用:
        - 缓存已搜索的论文
        - 避免重复请求API
        - 为验证功能提供数据源

    格式:
        {
            "论文ID": {
                "title": "标题",
                "bibtex": "@Article{...}",
                "abstract": "摘要",
                ...
            }
        }
    """

    _instance = None  # 单例实例
    _data = {}        # 缓存数据

    def __new__(cls):
        """单例模式：确保全局只有一个缓存实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()  # 加载缓存
        return cls._instance

    def _load(self):
        """从文件加载缓存"""
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
            except:
                self._data = {}  # 文件损坏，使用空缓存

    def _save(self):
        """保存缓存到文件"""
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def get(self, key: str) -> dict | None:
        """
        获取缓存

        参数:
            key: 论文ID（从BibTeX中提取）

        返回:
            dict: 论文信息（如果存在）
            None: 如果不存在
        """
        return self._data.get(key)

    def add(self, bibtex: str, paper_info: dict):
        """
        添加到缓存

        参数:
            bibtex: BibTeX格式引用
            paper_info: 论文详细信息

        作用:
            - 从BibTeX中提取论文ID
            - 存储论文信息
        """
        # 提取ID（第一行的大括号内容）
        # 示例: @Article{Vaswani2017, -> 提取 "Vaswani2017"
        lines = bibtex.strip().split('\n')
        if lines:
            first_line = lines[0]
            if '{' in first_line:
                # 提取ID
                key = first_line.split('{')[1].split(',')[0].strip()
                if key:
                    self._data[key] = paper_info
                    self._save()


# ==================== API调用 ====================

def search_papers(query: str, limit: int = 5) -> list[dict]:
    """
    搜索论文（带限流保护）

    参数:
        query: 搜索关键词
            - 示例: "attention mechanism"
            - 作用: 搜索包含这些关键词的论文

        limit: 返回数量
            - 示例: 5
            - 作用: 最多返回多少篇论文
            - 默认: 5

    返回:
        list[dict]: 论文列表
            [
                {
                    "title": "标题",
                    "bibtex": "@Article{...}",
                    "abstract": "摘要",
                    "authors": ["作者1", "作者2"],
                    "venue": "会议/期刊",
                    "year": 2024,
                    "url": "链接"
                }
            ]

    流程:
        1. 等待限流器调度
        2. 发送HTTP请求
        3. 解析响应
        4. 从队列删除请求

    示例:
        >>> papers = search_papers("transformer", limit=2)
        >>> print(papers[0]['title'])
        "Attention Is All You Need"
    """
    # === 步骤1: 等待调度 ===
    request_id = rate_limiter.wait_for_turn()

    try:
        # === 步骤2: 准备请求 ===
        headers = {}
        if API_KEY:
            headers["X-API-KEY"] = API_KEY  # 添加API密钥

        params = {
            "query": query,  # 搜索关键词
            "limit": limit,  # 返回数量
            # 请求字段
            "fields": "title,citationStyles,abstract,authors,venue,year,url"
        }

        # === 步骤3: 发送请求 ===
        resp = requests.get(API_URL, params=params, timeout=30, headers=headers)
        resp.raise_for_status()  # 检查HTTP错误
        data = resp.json()

        # === 步骤4: 解析结果 ===
        papers = []
        for item in data.get("data", []):
            # 提取BibTeX
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

    finally:
        # === 步骤5: 清理队列 ===
        rate_limiter.done(request_id)


# ==================== MCP工具定义 ====================

@mcp.tool()
def search_bibtex_and_abstract(query: str, limit: int = 5) -> str:
    """
    搜索论文并获取BibTeX

    参数:
        query: 搜索关键词
            - 示例: "attention mechanism"
            - 必填: 是

        limit: 返回数量
            - 示例: 5
            - 必填: 否
            - 默认: 5

    返回:
        str: JSON格式字符串
            {
                "query": "搜索词",
                "count": 2,
                "papers": [
                    {
                        "title": "标题",
                        "bibtex": "@Article{...}",
                        "abstract": "摘要",
                        "authors": ["作者"],
                        "venue": "会议",
                        "year": 2024,
                        "url": "链接"
                    }
                ]
            }

    副作用:
        - 结果自动缓存到 .bibtex.json

    示例:
        >>> result = search_bibtex_and_abstract("transformer", 2)
        >>> print(result)
        {"query": "transformer", "count": 2, "papers": [...]}
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

    参数:
        bibtex_content: 完整的.bib文件内容
            - 示例: "@Article{Vaswani2017, ...}"
            - 必填: 是

    返回:
        str: JSON格式字符串
            {
                "valid": true,          # 是否全部有效
                "total": 3,             # 总数
                "matched_count": 2,     # 匹配数
                "mismatched_count": 1,  # 不匹配数
                "not_found_count": 0,   # 未找到数
                "matched": [...],       # 匹配的引用
                "mismatched": [...],    # 不匹配的引用
                "not_found": [...]      # 未找到的引用
            }

    前提:
        - 需要先使用 search_bibtex_and_abstract 搜索论文
        - 搜索结果会自动缓存

    示例:
        >>> bibtex = "@Article{Vaswani2017, title={Attention}, ...}"
        >>> result = verify_citations_with_mismatches(bibtex)
        >>> print(result)
        {"valid": true, "total": 1, ...}
    """
    cache = Cache()

    # 提取所有引用键（正则匹配）
    # 示例: @Article{Vaswani2017, -> 提取 "Vaswani2017"
    pattern = r'@\w+\{([^,]+),'
    keys = re.findall(pattern, bibtex_content)

    matched = []
    mismatched = []
    not_found = []

    for key in keys:
        cached = cache.get(key)

        if cached is None:
            # 缓存中没有
            not_found.append({
                "key": key,
                "reason": "未在缓存中找到"
            })
        else:
            # 提取输入BibTeX中的标题
            title_match = re.search(r'title\s*=\s*[{"]([^}"]+)[}"]', bibtex_content)
            input_title = title_match.group(1) if title_match else ""

            # 比较标题（不区分大小写）
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


@mcp.tool()
def get_queue_status() -> str:
    """
    获取请求队列状态

    参数:
        无

    返回:
        str: JSON格式字符串
            {
                "total": 3,         # 总请求数
                "pending": 2,       # 待处理数
                "next_time": 123.456  # 下次可用时间
            }

    作用:
        查看当前有多少请求在排队

    示例:
        >>> status = get_queue_status()
        >>> print(status)
        {"total": 3, "pending": 2, "next_time": 123.456}
    """
    status = rate_limiter.get_queue_status()
    return json.dumps(status, ensure_ascii=False, indent=2)


@mcp.tool()
def clear_request_queue() -> str:
    """
    清空请求队列

    参数:
        无

    返回:
        str: JSON格式字符串
            {
                "status": "success",
                "message": "请求队列已清空"
            }

    作用:
        删除所有待处理的请求
        通常在测试或队列堵塞时使用

    示例:
        >>> result = clear_request_queue()
        >>> print(result)
        {"status": "success", "message": "请求队列已清空"}
    """
    rate_limiter.clear_queue()
    return json.dumps({
        "status": "success",
        "message": "请求队列已清空"
    }, ensure_ascii=False, indent=2)


# ==================== 主程序 ====================

if __name__ == "__main__":
    # 启动信息（输出到stderr，不影响stdio通信）
    import sys
    print("启动 BibTeX MCP Server (CLI 模式)", file=sys.stderr)
    print(f"API Key: {'已设置' if API_KEY else '未设置'}", file=sys.stderr)
    print(f"缓存文件: {CACHE_FILE}", file=sys.stderr)
    print(f"队列文件: {QUEUE_FILE}", file=sys.stderr)

    # 启动MCP服务器（stdio模式）
    mcp.run(transport="stdio")
