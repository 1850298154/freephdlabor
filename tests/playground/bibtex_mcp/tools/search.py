"""
BibTeX 搜索工具模块（无状态，纯函数）
"""

import json
import sys
import os
from typing import Dict, Any

# 添加当前目录到路径以支持直接运行
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api.semantic_scholar import search_papers
from cache import CitationCache


def search_and_cache(query: str, limit: int = 5, cache: CitationCache = None) -> str:
    """
    搜索论文并获取 BibTeX（同时缓存）

    Args:
        query: 搜索关键词
        limit: 返回结果数量
        cache: 缓存管理器实例（可选）

    Returns:
        JSON格式的论文列表
    """
    papers = search_papers(query, limit)

    results = []
    citation_keys = []

    for paper in papers:
        citation_key = None
        if cache:
            citation_key = cache.add(paper)

        citation_keys.append(citation_key)

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
        "citation_keys": citation_keys
    }, ensure_ascii=False, indent=2)


def list_cached(cache: CitationCache) -> str:
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


def get_paper_by_key(citation_key: str, cache: CitationCache) -> str:
    """
    根据引用键获取缓存的论文

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
